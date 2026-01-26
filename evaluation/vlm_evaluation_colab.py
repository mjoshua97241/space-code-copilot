"""
Self-Contained Colab-Friendly VLM Evaluation Script
====================================================

Fully self-contained script for evaluating Hugging Face VLM on blueprint extraction.
All code is inline - no imports from local directories.

Focus: HF model evaluation (sabaridsnfuji/FloorPlanVisionAIAdaptor)
Optional: GPT-4o and Gemini 2.0 Flash (if API keys provided)

Colab Setup:
1) Clone repo:
   !git clone <your-repo-url> space-code-copilot
   %cd /content/space-code-copilot

2) Install deps (HF focus):
   !pip -q install -U pip
   !pip -q install -U "pydantic>=2.7,<3" "pymupdf>=1.24,<2" pillow pandas rapidfuzz
   
   # HF (GPU required) - choose CUDA version matching Colab runtime:
   !pip -q install -U torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   !pip -q install -U "huggingface-hub>=0.34,<1.0" transformers unsloth bitsandbytes

3) Set API keys (optional, only for GPT-4o/Gemini):
   import os
   os.environ["OPENAI_API_KEY"] = "..."  # Optional
   os.environ["GOOGLE_API_KEY"] = "..."  # Optional

4) Run:
   !python evaluation/vlm_evaluation_colab.py --run-hf
   # Or with all models:
   !python evaluation/vlm_evaluation_colab.py --run-openai --run-gemini --run-hf
"""

from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Union

import pandas as pd

# ==================================================================
# Pydantic Models (inline)
# ==================================================================

try:
    from pydantic import BaseModel, Field
except ImportError:
    raise ImportError("pydantic>=2.7 required. Install: pip install pydantic>=2.7,<3")


class Room(BaseModel):
    id: str = Field(..., description="Unique room identifier")
    name: str = Field(..., description="Room name")
    type: str = Field(..., description="Room type/category")
    level: int = Field(..., ge=1, description="Floor level (1-based)")
    area_m2: float = Field(..., gt=0, description="Area in square meters")

    class Config:
        frozen = False


class Overlay(BaseModel):
    id: str = Field(..., description="Element ID")
    type: Literal["room", "door"] = Field(..., description="Element type")
    x: int = Field(..., ge=0, description="X coordinate in pixels")
    y: int = Field(..., ge=0, description="Y coordinate in pixels")
    width: int = Field(..., gt=0, description="Width in pixels")
    height: int = Field(..., gt=0, description="Height in pixels")
    room_name: Optional[str] = None
    room_type: Optional[str] = None

    class Config:
        frozen = False


class ExtractionConfidence(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0)
    name_confidence: float = Field(..., ge=0.0, le=1.0)
    type_confidence: float = Field(..., ge=0.0, le=1.0)
    area_confidence: float = Field(..., ge=0.0, le=1.0)

    class Config:
        frozen = False


class BlueprintExtractionResult(BaseModel):
    rooms: List[Room] = Field(..., description="Extracted rooms")
    confidence: ExtractionConfidence = Field(..., description="Confidence scores")
    overlays: List[Overlay] = Field(default_factory=list)
    scale_used: float = Field(..., description="Scale factor applied")
    scale_source: Literal["default", "user_input", "auto_detected"] = Field(...)
    extraction_metadata: Dict[str, Any] = Field(default_factory=dict)
    note: str = Field(
        default="Extraction is approximate. CSV pipeline remains ground truth."
    )

    class Config:
        frozen = False


# ==================================================================
# Constants
# ==================================================================

VALID_ROOM_TYPES = {
    "bedroom", "living", "kitchen", "bathroom", "office", "meeting", "corridor", "storage", "other"
}
MIN_ROOM_AREA_M2 = 2.0
MAX_ROOM_AREA_M2 = 500.0
FUZZY_MATCH_THRESHOLD = 85


# ==================================================================
# Image Processing (inline from blueprint_extractor)
# ==================================================================

try:
    from PIL import Image
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("pillow and pymupdf required. Install: pip install pillow pymupdf>=1.24,<2")


def _get_image_dimensions(image_path: Union[str, Path], page_index: Optional[int] = None) -> Tuple[int, int]:
    """Get image dimensions (width, height) in pixels."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if image_path.suffix.lower() == '.pdf':
        doc = fitz.open(str(image_path))
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {image_path}")
        
        if page_index is not None:
            if page_index < 0 or page_index >= len(doc):
                doc.close()
                raise ValueError(f"Page index {page_index} out of range (0-{len(doc)-1})")
            pages_to_extract = [page_index]
        else:
            pages_to_extract = list(range(len(doc)))
        
        page_images = []
        mat = fitz.Matrix(2.0, 2.0)
        
        for page_num in pages_to_extract:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            page_img = Image.open(io.BytesIO(img_data))
            page_images.append(page_img)
        
        doc.close()
        
        if len(page_images) == 1:
            img = page_images[0]
        else:
            total_width = max(img.width for img in page_images)
            total_height = sum(img.height for img in page_images)
            img = Image.new('RGB', (total_width, total_height), color='white')
    else:
        img = Image.open(image_path)
    
    return (img.width, img.height)


def _load_image_for_hf(image_path: Union[str, Path], page_index: Optional[int] = None) -> Image.Image:
    """Load image as PIL Image for HF model."""
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    if image_path.suffix.lower() == '.pdf':
        doc = fitz.open(str(image_path))
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {image_path}")
        
        if page_index is not None:
            if page_index < 0 or page_index >= len(doc):
                doc.close()
                raise ValueError(f"Page index {page_index} out of range")
            pages_to_extract = [page_index]
        else:
            pages_to_extract = [0]  # HF: use first page only
        
        page = doc[pages_to_extract[0]]
        zoom = 2.0
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        doc.close()
    else:
        image = Image.open(image_path)
    
    return image


# ==================================================================
# Prompt Building & Parsing (inline from blueprint_extractor)
# ==================================================================

def _build_extraction_prompt(scale: float) -> str:
    """Build prompt for VLM extraction."""
    return f"""Analyze this architectural blueprint image and extract all rooms with their properties.

**Your task:**
1. **Read room labels**: Identify all rooms by reading their labels (e.g., "Office 101", "Meeting Room", "Bedroom 1", "WC", "Kitchen").
2. **Classify room types**: For each room, classify it into one of these types:
    - "bedroom" (sleeping rooms, BR, Bedroom)
    - "living" (living room, family room, Living Area)
    - "kitchen" (cooking areas, Kitchen)
    - "bathroom" (WC, toilet, shower, T&B, Toilet & Bath, Bath, Bathroom, CR, Comfort Room)
    - "office" (work spaces, study rooms, Office)
    - "meeting" (conference rooms, meeting spaces, Meeting Room)
    - "corridor" (hallways, passages, Corridor, Hallway)
    - "storage" (closets, storage areas, Storage, Closet)
    - "other" (any other room type)
3. **Read dimensions**: Find dimension annotations and associate with rooms.
4. **Calculate areas**: Apply scale factor: {scale} (1 unit on blueprint = {scale} meters).
5. **Assign floor level**: Determine floor level from plan titles (default: level 1).
6. **Locate room label bounding boxes**: Provide pixel coordinates (x, y, width, height) for label text, or null if unclear.

**Output format**: Return a JSON object:
{{
    "plan_title": "GROUND FLOOR PLAN",
    "rooms": [
        {{
            "id": "R101",
            "name": "Office 101",
            "type": "office",
            "level": 1,
            "area_m2": 12.0,
            "label_bbox": {{"x": 150, "y": 200, "width": 80, "height": 20}} or null
        }}
    ]
}}

Return ONLY valid JSON, no additional text.
"""


def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """Parse LLM response text into structured JSON."""
    text = response_text.strip()
    
    if "```json" in text:
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    elif "```" in text:
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON: {e}\nResponse: {response_text[:500]}")


def _normalize_room_type(room_type: str, room_name: str = "") -> str:
    """Normalize room type by handling abbreviations."""
    if not room_type:
        return "other"
    
    normalized = room_type.lower().strip()
    name_lower = room_name.lower().strip() if room_name else ""
    
    bathroom_keywords = ["t&b", "t & b", "tb", "wc", "water closet", "cr", "comfort room", "toilet", "bath", "bathroom"]
    if any(kw in normalized or kw in name_lower for kw in bathroom_keywords):
        return "bathroom"
    
    bedroom_keywords = ["bedroom", "br", "bed"]
    if any(kw in normalized or kw in name_lower for kw in bedroom_keywords):
        return "bedroom"
    
    living_keywords = ["living", "family room", "dining"]
    if any(kw in normalized or kw in name_lower for kw in living_keywords):
        return "living"
    
    kitchen_keywords = ["kitchen", "cooking"]
    if any(kw in normalized or kw in name_lower for kw in kitchen_keywords):
        return "kitchen"
    
    office_keywords = ["office", "study", "work"]
    if any(kw in normalized or kw in name_lower for kw in office_keywords):
        return "office"
    
    meeting_keywords = ["meeting", "conference", "boardroom"]
    if any(kw in normalized or kw in name_lower for kw in meeting_keywords):
        return "meeting"
    
    corridor_keywords = ["corridor", "hallway", "hall", "passage"]
    if any(kw in normalized or kw in name_lower for kw in corridor_keywords):
        return "corridor"
    
    storage_keywords = ["storage", "closet", "pantry"]
    if any(kw in normalized or kw in name_lower for kw in storage_keywords):
        return "storage"
    
    if normalized in VALID_ROOM_TYPES:
        return normalized
    
    return "other"


def _normalize_floor_level(level: Any, plan_title: str = "") -> int:
    """Normalize floor level."""
    if level is not None:
        try:
            level_int = int(level)
            if level_int >= 1:
                return level_int
        except (ValueError, TypeError):
            pass
    
    if plan_title:
        title_upper = plan_title.upper()
        if any(kw in title_upper for kw in ["GROUND FLOOR", "GROUND", "FIRST FLOOR", "1ST FLOOR"]):
            return 1
        if any(kw in title_upper for kw in ["SECOND FLOOR", "2ND FLOOR", "2ND"]):
            return 2
        if any(kw in title_upper for kw in ["THIRD FLOOR", "3RD FLOOR", "3RD"]):
            return 3
        if any(kw in title_upper for kw in ["FOURTH FLOOR", "4TH FLOOR", "4TH"]):
            return 4
        floor_match = re.search(r'(?:FLOOR|LEVEL|FL)\s*(\d+)', title_upper)
        if floor_match:
            try:
                return int(floor_match.group(1))
            except ValueError:
                pass
    
    return 1


def _validate_and_convert_rooms(raw_rooms: List[Dict[str, Any]], plan_title: str = "") -> List[Room]:
    """Validate and convert raw room dictionaries to Room models."""
    validated_rooms = []
    for idx, room_dict in enumerate(raw_rooms):
        try:
            if "id" not in room_dict or not room_dict["id"]:
                room_dict["id"] = f"R{100 + idx + 1}"
            
            if "name" not in room_dict or not room_dict.get("name", "").strip():
                room_dict["name"] = f"Room {room_dict.get('id', idx + 1)}"
            else:
                room_dict["name"] = str(room_dict["name"]).strip()
            
            room_type_raw = room_dict.get("type", "")
            room_name = room_dict.get("name", "")
            room_dict["type"] = _normalize_room_type(room_type_raw, room_name)
            
            if room_dict["type"] not in VALID_ROOM_TYPES:
                room_dict["type"] = "other"
            
            level_raw = room_dict.get("level", None)
            room_dict["level"] = _normalize_floor_level(level_raw, plan_title)
            
            if "area_m2" not in room_dict:
                continue
            
            try:
                area = float(room_dict["area_m2"])
            except (ValueError, TypeError):
                continue
            
            if area < MIN_ROOM_AREA_M2 or area > MAX_ROOM_AREA_M2:
                continue
            
            room = Room(
                id=str(room_dict["id"]),
                name=str(room_dict["name"]),
                type=str(room_dict["type"]),
                level=int(room_dict["level"]),
                area_m2=float(area)
            )
            validated_rooms.append(room)
        except Exception:
            continue
    
    return validated_rooms


def _calculate_confidence_scores(rooms: List[Room], raw_response: Dict[str, Any]) -> Dict[str, float]:
    """Calculate confidence scores."""
    if not rooms:
        return {"overall": 0.0, "name_confidence": 0.0, "type_confidence": 0.0, "area_confidence": 0.0}
    
    total_rooms = len(rooms)
    
    generic_patterns = ["room", "r", "space"]
    generic_count = sum(
        1 for r in rooms
        if any(r.name.lower().strip().startswith(p) and len(r.name.lower().strip()) <= len(p) + 3
               for p in generic_patterns)
    )
    name_confidence = max(0.7, 1.0 - (generic_count / total_rooms * 0.3))
    
    other_count = sum(1 for r in rooms if r.type == "other")
    type_confidence = max(0.6, 1.0 - (other_count / total_rooms * 0.4))
    
    near_min = sum(1 for r in rooms if r.area_m2 < MIN_ROOM_AREA_M2 * 1.5)
    near_max = sum(1 for r in rooms if r.area_m2 > MAX_ROOM_AREA_M2 * 0.8)
    area_penalty = (near_min + near_max) / total_rooms * 0.2
    area_confidence = max(0.8, 1.0 - area_penalty)
    
    overall = name_confidence * 0.3 + type_confidence * 0.4 + area_confidence * 0.3
    overall = max(0.0, min(1.0, overall))
    
    return {
        "overall": overall,
        "name_confidence": name_confidence,
        "type_confidence": type_confidence,
        "area_confidence": area_confidence
    }


def _create_overlays_from_label_bbox(
    raw_rooms: List[Dict[str, Any]],
    validated_rooms: List[Room],
    image_width: int,
    image_height: int
) -> List[Overlay]:
    """Create Overlay objects from label_bbox."""
    overlays = []
    room_by_id = {room.id: room for room in validated_rooms}
    
    for raw_room in raw_rooms:
        room_id = raw_room.get("id")
        if not room_id:
            continue
        
        room = room_by_id.get(room_id)
        if not room:
            continue
        
        label_bbox = raw_room.get("label_bbox")
        if not label_bbox or label_bbox is None:
            continue
        
        if not isinstance(label_bbox, dict):
            continue
        
        try:
            x = int(label_bbox.get("x", 0))
            y = int(label_bbox.get("y", 0))
            width = int(label_bbox.get("width", 0))
            height = int(label_bbox.get("height", 0))
        except (ValueError, TypeError):
            continue
        
        if width <= 0 or height <= 0:
            continue
        
        x = max(0, min(x, image_width - 1))
        y = max(0, min(y, image_height - 1))
        width = min(width, image_width - x)
        height = min(height, image_height - y)
        
        if width <= 0 or height <= 0:
            continue
        
        bbox_area = width * height
        image_area = image_width * image_height
        if bbox_area > image_area * 0.5:
            continue
        
        if width < 10 or height < 10:
            continue
        
        try:
            overlay = Overlay(
                id=room.id,
                type="room",
                x=x,
                y=y,
                width=width,
                height=height,
                room_name=room.name,
                room_type=room.type
            )
            overlays.append(overlay)
        except Exception:
            continue
    
    return overlays


# ==================================================================
# Metrics Functions (inline from vlm_extraction_metrics)
# ==================================================================

try:
    from rapidfuzz import fuzz, process
except ImportError:
    raise ImportError("rapidfuzz required. Install: pip install rapidfuzz")


def match_rooms(
    extracted: List[Room],
    ground_truth: List[Room],
    fuzzy_threshold: int = FUZZY_MATCH_THRESHOLD
) -> Tuple[List[Tuple[Room, Room]], List[Room], List[Room]]:
    """Match extracted rooms to ground truth by name using fuzzy matching."""
    matched_pairs = []
    unmatched_extracted = []
    unmatched_ground_truth = list(ground_truth)
    
    ground_truth_by_name_exact = {r.name.lower().strip(): r for r in ground_truth}
    matched_gt_indices = set()
    
    for ext_room in extracted:
        ext_name_lower = ext_room.name.lower().strip()
        if ext_name_lower in ground_truth_by_name_exact:
            gt_room = ground_truth_by_name_exact[ext_name_lower]
            matched_pairs.append((ext_room, gt_room))
            matched_gt_indices.add(id(gt_room))
        else:
            unmatched_extracted.append(ext_room)
    
    unmatched_gt_for_fuzzy = [gt for gt in unmatched_ground_truth if id(gt) not in matched_gt_indices]
    
    if unmatched_gt_for_fuzzy and unmatched_extracted:
        fuzzy_unmatched_extracted = []
        for ext_room in unmatched_extracted:
            best_match = process.extractOne(
                ext_room.name,
                [gt.name for gt in unmatched_gt_for_fuzzy],
                scorer=fuzz.ratio,
                score_cutoff=fuzzy_threshold
            )
            if best_match:
                matched_gt_name = best_match[0]
                matched_gt_room = next(gt for gt in unmatched_gt_for_fuzzy if gt.name == matched_gt_name)
                matched_pairs.append((ext_room, matched_gt_room))
                matched_gt_indices.add(id(matched_gt_room))
            else:
                fuzzy_unmatched_extracted.append(ext_room)
        unmatched_extracted = fuzzy_unmatched_extracted
    
    unmatched_ground_truth = [gt for gt in ground_truth if id(gt) not in matched_gt_indices]
    
    return matched_pairs, unmatched_extracted, unmatched_ground_truth


def calculate_area_accuracy(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate area accuracy using MAPE."""
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    if not matched_pairs:
        return 0.0
    
    percentage_errors = []
    for ext_room, gt_room in matched_pairs:
        if gt_room.area_m2 > 0:
            error_pct = abs(ext_room.area_m2 - gt_room.area_m2) / gt_room.area_m2
            percentage_errors.append(error_pct)
    
    if not percentage_errors:
        return 0.0
    
    mape = sum(percentage_errors) / len(percentage_errors)
    accuracy = max(0.0, min(1.0, 1.0 - mape))
    return accuracy


def calculate_recall(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate recall: percentage of ground truth rooms found."""
    if not ground_truth_rooms:
        return 0.0
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    return len(matched_pairs) / len(ground_truth_rooms)


def calculate_precision(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate precision: percentage of extracted rooms that are valid."""
    if not extracted_rooms:
        return 0.0
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    return len(matched_pairs) / len(extracted_rooms)


def calculate_type_match_rate(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate type match rate."""
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    if not matched_pairs:
        return 0.0
    type_matches = sum(1 for ext_room, gt_room in matched_pairs if ext_room.type == gt_room.type)
    return type_matches / len(matched_pairs)


def calculate_name_match_rate(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate name match rate."""
    if not ground_truth_rooms:
        return 0.0
    matched_pairs, _, _ = match_rooms(extracted_rooms, ground_truth_rooms)
    return len(matched_pairs) / len(ground_truth_rooms)


def calculate_semantic_understanding_score(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """Evaluate semantic understanding."""
    if not extracted_rooms:
        return 0.0
    
    other_type_count = sum(1 for r in extracted_rooms if r.type == "other")
    other_type_ratio = other_type_count / len(extracted_rooms)
    type_quality_score = 1.0 - (other_type_ratio * 0.5)
    
    type_match_rate = calculate_type_match_rate(extracted_rooms, ground_truth_rooms)
    type_confidence = extraction_result.confidence.type_confidence
    overall_confidence = extraction_result.confidence.overall
    
    semantic_score = (
        type_quality_score * 0.4 +
        type_match_rate * 0.3 +
        type_confidence * 0.2 +
        overall_confidence * 0.1
    )
    
    return max(0.0, min(1.0, semantic_score))


def calculate_confidence_calibration(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """Measure confidence calibration."""
    recall = calculate_recall(extracted_rooms, ground_truth_rooms)
    precision = calculate_precision(extracted_rooms, ground_truth_rooms)
    area_accuracy = calculate_area_accuracy(extracted_rooms, ground_truth_rooms)
    type_match_rate = calculate_type_match_rate(extracted_rooms, ground_truth_rooms)
    
    actual_accuracy = (recall + precision + area_accuracy + type_match_rate) / 4.0
    predicted_accuracy = extraction_result.confidence.overall
    
    calibration_error = abs(predicted_accuracy - actual_accuracy)
    calibration_score = max(0.0, min(1.0, 1.0 - calibration_error))
    
    return calibration_score


def calculate_composite_score(metrics: Dict[str, float], weights: Optional[Dict[str, float]] = None) -> float:
    """Calculate weighted composite score."""
    default_weights = {
        "area_accuracy": 0.25,
        "recall": 0.20,
        "precision": 0.20,
        "type_match_rate": 0.15,
        "semantic_understanding_score": 0.10,
        "confidence_calibration": 0.05,
        "name_match_rate": 0.05,
    }
    
    if weights is None:
        weights = default_weights
    
    total_weight = sum(weights.values())
    if total_weight > 0:
        weights = {k: v / total_weight for k, v in weights.items()}
    
    composite = 0.0
    for metric_name, weight in weights.items():
        if metric_name in metrics:
            composite += metrics[metric_name] * weight
    
    return max(0.0, min(1.0, composite))


def calculate_all_metrics(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult,
    latency_seconds: Optional[float] = None
) -> Dict[str, float]:
    """Calculate all metrics for a single extraction."""
    metrics = {
        "area_accuracy": calculate_area_accuracy(extracted_rooms, ground_truth_rooms),
        "recall": calculate_recall(extracted_rooms, ground_truth_rooms),
        "precision": calculate_precision(extracted_rooms, ground_truth_rooms),
        "type_match_rate": calculate_type_match_rate(extracted_rooms, ground_truth_rooms),
        "name_match_rate": calculate_name_match_rate(extracted_rooms, ground_truth_rooms),
        "semantic_understanding_score": calculate_semantic_understanding_score(
            extracted_rooms, ground_truth_rooms, extraction_result
        ),
        "confidence_calibration": calculate_confidence_calibration(
            extracted_rooms, ground_truth_rooms, extraction_result
        ),
    }
    
    if latency_seconds is not None:
        latency_score = max(0.0, min(1.0, 1.0 - (latency_seconds - 5.0) / 25.0))
        metrics["latency_score"] = latency_score
        metrics["latency_seconds"] = latency_seconds
    
    metrics["composite_score"] = calculate_composite_score(metrics)
    
    return metrics


# ==================================================================
# CSV Loading (simplified)
# ==================================================================

def load_rooms_from_csv(csv_path: Path) -> List[Room]:
    """Load rooms from CSV file."""
    rooms = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                room = Room(
                    id=row["id"].strip(),
                    name=row["name"].strip(),
                    type=row["type"].strip(),
                    level=int(row["level"]),
                    area_m2=float(row["area_m2"])
                )
                rooms.append(room)
            except Exception:
                continue
    return rooms


# ==================================================================
# Hugging Face VLM Wrapper (inline)
# ==================================================================

def create_hf_extractor(
    model_name: str = "sabaridsnfuji/FloorPlanVisionAIAdaptor",
    device: Optional[str] = None,
    load_in_4bit: Optional[bool] = None,
):
    """
    Create HF extractor function.
    
    Requires CUDA GPU (Unsloth requirement).
    """
    try:
        import torch
        from transformers import AutoTokenizer
    except ImportError as e:
        raise ImportError(f"Required packages missing: {e}\nInstall: pip install transformers torch")
    
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    
    if device != "cuda":
        raise RuntimeError(
            "Hugging Face FloorPlanVisionAIAdaptor evaluation requires a CUDA-capable GPU. "
            "Unsloth does not run on CPU."
        )
    
    if load_in_4bit is None:
        load_in_4bit = True  # Default to 4-bit for CUDA
    
    print(f"🔄 Loading Hugging Face model: {model_name}")
    print(f"   Device: {device}")
    print(f"   load_in_4bit: {load_in_4bit}")
    
    try:
        # Import Unsloth lazily
        from unsloth import FastVisionModel
        
        model, tokenizer = FastVisionModel.from_pretrained(
            model_name,
            load_in_4bit=load_in_4bit,
            use_gradient_checkpointing="unsloth"
        )
        FastVisionModel.for_inference(model)
        model = model.to(device)
        print(f"   ✓ Model loaded successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to load Hugging Face model: {e}")
    
    def extractor(image_path: str, scale_override: float = 1.0) -> BlueprintExtractionResult:
        """Extract rooms from blueprint using HF model."""
        image_path_obj = Path(image_path)
        if not image_path_obj.exists():
            raise FileNotFoundError(f"Image file not found: {image_path}")
        
        # Load image
        try:
            image = _load_image_for_hf(image_path)
        except Exception as e:
            raise ValueError(f"Failed to load image: {e}")
        
        # Build prompt
        prompt = _build_extraction_prompt(scale_override)
        
        # Format messages for HF model
        messages_hf = [
            {"role": "user", "content": [
                {"type": "image"},
                {"type": "text", "text": prompt}
            ]}
        ]
        
        # Tokenize
        try:
            input_text = tokenizer.apply_chat_template(
                messages_hf,
                add_generation_prompt=True
            )
            inputs = tokenizer(
                image,
                input_text,
                add_special_tokens=False,
                return_tensors="pt",
            ).to(device)
        except Exception as e:
            raise RuntimeError(f"Tokenization failed: {e}")
        
        # Generate
        try:
            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=2048,
                    use_cache=True,
                    temperature=0.0,
                )
        except Exception as e:
            raise RuntimeError(f"Model generation failed: {e}")
        
        # Decode
        response_text = tokenizer.decode(output[0], skip_special_tokens=True)
        
        # Extract JSON
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            response_text = json_match.group(0)
        
        # Parse
        try:
            parsed_response = _parse_llm_response(response_text)
        except Exception as e:
            raise ValueError(f"Failed to parse model response: {e}\nResponse: {response_text[:500]}")
        
        # Extract rooms
        raw_rooms = parsed_response.get("rooms", [])
        if not raw_rooms:
            raise ValueError("No rooms extracted from blueprint")
        
        plan_title = parsed_response.get("plan_title", "") or parsed_response.get("title", "")
        
        # Validate
        validated_rooms = _validate_and_convert_rooms(raw_rooms, plan_title=plan_title)
        if not validated_rooms:
            raise ValueError("No valid rooms extracted after validation")
        
        # Confidence
        confidence = _calculate_confidence_scores(validated_rooms, parsed_response)
        confidence_obj = ExtractionConfidence(**confidence)
        
        # Overlays
        overlays = []
        try:
            image_width, image_height = _get_image_dimensions(image_path)
            overlays = _create_overlays_from_label_bbox(
                raw_rooms=raw_rooms,
                validated_rooms=validated_rooms,
                image_width=image_width,
                image_height=image_height
            )
        except Exception:
            overlays = []
        
        # Build result
        result = BlueprintExtractionResult(
            rooms=validated_rooms,
            confidence=confidence_obj,
            scale_used=scale_override,
            scale_source="user_input",
            overlays=overlays,
            extraction_metadata={
                "model_used": model_name,
                "provider": "huggingface",
                "device": device,
            }
        )
        
        return result
    
    return extractor


# ==================================================================
# Golden Dataset Loading
# ==================================================================

def load_golden_dataset(data_dir: Path) -> pd.DataFrame:
    """Load golden dataset from JSON."""
    input_path = data_dir / "vlm_golden_dataset.json"
    if not input_path.exists():
        raise FileNotFoundError(f"Golden dataset not found at {input_path}")
    
    with open(input_path, "r") as f:
        dataset_dict = json.load(f)
    
    for entry in dataset_dict:
        entry["ground_truth_rooms"] = [Room(**r) for r in entry["ground_truth_rooms"]]
    
    df = pd.DataFrame(dataset_dict)
    print(f"✔ Golden dataset loaded: {len(df)} plans from {input_path}")
    return df


# ==================================================================
# Evaluation Logic
# ==================================================================

def evaluate_vlm_extraction(
    extractor_func: Callable[[str, float], BlueprintExtractionResult],
    golden_dataset_df: pd.DataFrame,
    model_name: str,
    delay_between_extractions: float = 1.0,
) -> Dict[str, Any]:
    """Evaluate VLM extraction."""
    print("\n" + "=" * 60)
    print(f"Evaluation: {model_name}")
    print("=" * 60)
    print(f"⚠ Rate limiting: {delay_between_extractions:.1f}s delay between extractions")
    
    per_image_metrics: List[Dict[str, Any]] = []
    latencies: List[float] = []
    successful = 0
    failed = 0
    
    for idx, row in golden_dataset_df.iterrows():
        plan_name = row.get("plan_name", f"plan_{idx}")
        image_path = row["image_path"]
        scale = float(row.get("scale", 1.0))
        ground_truth_rooms = row["ground_truth_rooms"]
        
        print(f"\n[{idx+1}/{len(golden_dataset_df)}] Processing: {plan_name}")
        start = time.time()
        try:
            result = extractor_func(image_path, scale)
            latency = time.time() - start
            latencies.append(latency)
            successful += 1
            
            extracted_rooms = result.rooms
            metrics = calculate_all_metrics(
                extracted_rooms=extracted_rooms,
                ground_truth_rooms=ground_truth_rooms,
                extraction_result=result,
                latency_seconds=latency,
            )
            metrics.update({
                "plan_name": plan_name,
                "image_path": image_path,
                "extracted_count": len(extracted_rooms),
                "ground_truth_count": len(ground_truth_rooms),
            })
            per_image_metrics.append(metrics)
            
            print(f"  ✓ Extracted {len(extracted_rooms)} rooms in {latency:.2f}s")
            print(f"    Recall: {metrics['recall']*100:.2f}%, Precision: {metrics['precision']*100:.2f}%")
            print(f"    Area accuracy: {metrics['area_accuracy']*100:.2f}%, Type match: {metrics['type_match_rate']*100:.2f}%")
        except Exception as e:
            latency = time.time() - start
            latencies.append(latency)
            failed += 1
            
            per_image_metrics.append({
                "plan_name": plan_name,
                "image_path": image_path,
                "error": str(e),
                "extracted_count": 0,
                "ground_truth_count": len(ground_truth_rooms),
            })
            print(f"  ✗ Extraction failed: {e}")
        
        if idx < len(golden_dataset_df) - 1:
            print(f"    Waiting {delay_between_extractions:.1f}s...")
            time.sleep(delay_between_extractions)
    
    metric_rows = [m for m in per_image_metrics if "error" not in m]
    if not metric_rows:
        print("❌ No successful extractions!")
        return {
            "model_name": model_name,
            "metrics_results": {},
            "per_image_metrics": per_image_metrics,
            "avg_latency": sum(latencies) / max(1, len(latencies)),
            "evaluated_at": datetime.now().isoformat(),
            "golden_dataset_size": len(golden_dataset_df),
            "successful_extractions": successful,
            "failed_extractions": failed,
        }
    
    keys = [
        "area_accuracy", "recall", "precision", "type_match_rate",
        "name_match_rate", "semantic_understanding_score", "confidence_calibration",
        "avg_latency", "composite_score",
    ]
    metrics_results: Dict[str, Any] = {}
    for k in keys:
        vals = [m[k] for m in metric_rows if k in m]
        if vals:
            metrics_results[k] = float(sum(vals) / len(vals))
    
    avg_latency = float(sum(latencies) / max(1, len(latencies)))
    metrics_results["avg_latency"] = avg_latency
    
    print(f"\n✔ Evaluation complete for {model_name}")
    print(f"   Average latency: {avg_latency:.2f}s")
    if "composite_score" in metrics_results:
        print(f"   Composite score: {metrics_results['composite_score']:.3f}")
    
    return {
        "model_name": model_name,
        "metrics_results": metrics_results,
        "per_image_metrics": per_image_metrics,
        "avg_latency": avg_latency,
        "evaluated_at": datetime.now().isoformat(),
        "golden_dataset_size": len(golden_dataset_df),
        "successful_extractions": successful,
        "failed_extractions": failed,
    }


def compare_models(results: List[Dict[str, Any]]) -> None:
    """Compare evaluation results."""
    if not results:
        print("\n❌ No evaluation results to compare.")
        return
    
    rows = []
    for r in results:
        m = r.get("metrics_results", {}) or {}
        rows.append({
            "Model": r.get("model_name"),
            "Composite Score": m.get("composite_score"),
            "Recall": m.get("recall"),
            "Precision": m.get("precision"),
            "Area Accuracy": m.get("area_accuracy"),
            "Type Match": m.get("type_match_rate"),
            "Semantic Score": m.get("semantic_understanding_score"),
            "Avg Latency": m.get("avg_latency"),
            "Success": f"{r.get('successful_extractions', 0)}/{r.get('golden_dataset_size', 0)}",
        })
    
    df = pd.DataFrame(rows)
    
    def pct(x: Any) -> Any:
        return None if x is None else f"{float(x)*100:.2f}%"
    
    for col in ["Recall", "Precision", "Area Accuracy", "Type Match"]:
        df[col] = df[col].apply(pct)
    
    if "Composite Score" in df.columns:
        df["Composite Score"] = df["Composite Score"].apply(lambda x: None if x is None else f"{float(x):.3f}")
    if "Avg Latency" in df.columns:
        df["Avg Latency"] = df["Avg Latency"].apply(lambda x: None if x is None else f"{float(x):.2f}s")
    
    print("\n" + "=" * 60)
    print("Model Comparison")
    print("=" * 60)
    print(df.to_string(index=False))
    
    if rows:
        best_model = max(results, key=lambda r: r.get("metrics_results", {}).get("composite_score", 0))
        print(f"\n🏆 Best Model: {best_model['model_name']} (composite score: {best_model['metrics_results']['composite_score']:.3f})")


def save_results(results: List[Dict[str, Any]], results_dir: Path) -> Path:
    """Save evaluation results."""
    results_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = results_dir / f"vlm_evaluation_results_{timestamp}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    return out_path


# ==================================================================
# Main
# ==================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Self-contained Colab VLM evaluation")
    parser.add_argument("--repo-root", default=None, help="Path to repo root (defaults to inferred)")
    parser.add_argument("--run-openai", action="store_true", help="Run GPT-4o (requires OPENAI_API_KEY)")
    parser.add_argument("--run-gemini", action="store_true", help="Run Gemini (requires GOOGLE_API_KEY)")
    parser.add_argument("--run-hf", action="store_true", help="Run HF (requires CUDA GPU)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between extractions (seconds)")
    args = parser.parse_args()
    
    # Resolve paths
    if args.repo_root:
        repo_root = Path(args.repo_root).expanduser().resolve()
    else:
        repo_root = Path(__file__).resolve().parent.parent
    
    data_dir = repo_root / "evaluation" / "data"
    results_dir = repo_root / "evaluation" / "results"
    
    print("=" * 60)
    print("VLM Extraction Evaluation (Colab - Self-Contained)")
    print("=" * 60)
    
    # Load golden dataset
    print("\n📊 Loading golden dataset...")
    try:
        golden_df = load_golden_dataset(data_dir)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print("   Tip: Ensure evaluation/data/vlm_golden_dataset.json exists")
        return
    
    if golden_df.empty:
        print("❌ Golden dataset is empty. Exiting.")
        return
    
    results: List[Dict[str, Any]] = []
    
    # Hugging Face (primary focus)
    if args.run_hf:
        hf_available = False
        hf_import_error: Optional[str] = None
        
        try:
            import torch
            if not torch.cuda.is_available():
                hf_import_error = "CUDA not available. Colab HF eval requires GPU runtime."
            else:
                import unsloth  # noqa: F401
                hf_available = True
        except Exception as e:
            hf_import_error = str(e)
        
        if not hf_available:
            print("\n⚠ Hugging Face evaluation not available.")
            if hf_import_error:
                print(f"   Reason: {hf_import_error}")
            print("   Tip: In Colab, set Runtime -> Change runtime type -> GPU")
        else:
            print("\n" + "=" * 60)
            print("Evaluating Hugging Face FloorPlanVisionAIAdaptor...")
            print("=" * 60)
            
            try:
                hf_extractor = create_hf_extractor(device="cuda")
                
                def extractor_hf(image_path: str, scale_override: float = 1.0):
                    return hf_extractor(image_path, scale_override)
                
                results.append(
                    evaluate_vlm_extraction(
                        extractor_func=extractor_hf,
                        golden_dataset_df=golden_df,
                        model_name="hf-floorplan-vision-adaptor",
                        delay_between_extractions=max(args.delay, 0.5),
                    )
                )
            except Exception as e:
                print(f"❌ Hugging Face evaluation failed: {e}")
                import traceback
                traceback.print_exc()
    
    # GPT-4o (optional, requires langchain)
    if args.run_openai:
        if os.getenv("OPENAI_API_KEY"):
            try:
                from langchain_openai import ChatOpenAI
                from langchain_core.messages import HumanMessage
                
                def extractor_gpt4o(image_path: str, scale_override: float = 1.0):
                    # Simplified GPT-4o extraction (would need full blueprint_extractor logic)
                    raise NotImplementedError("GPT-4o extraction not fully implemented in self-contained script")
                
                print("\n⚠ GPT-4o extraction requires full blueprint_extractor logic.")
                print("   Skipping GPT-4o evaluation in self-contained script.")
            except ImportError:
                print("\n⚠ langchain-openai not installed. Skipping GPT-4o.")
        else:
            print("\n⚠ OPENAI_API_KEY not set. Skipping GPT-4o evaluation.")
    
    # Gemini (optional, requires langchain)
    if args.run_gemini:
        if os.getenv("GOOGLE_API_KEY"):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                from langchain_core.messages import HumanMessage
                
                def extractor_gemini(image_path: str, scale_override: float = 1.0):
                    # Simplified Gemini extraction (would need full blueprint_extractor logic)
                    raise NotImplementedError("Gemini extraction not fully implemented in self-contained script")
                
                print("\n⚠ Gemini extraction requires full blueprint_extractor logic.")
                print("   Skipping Gemini evaluation in self-contained script.")
            except ImportError:
                print("\n⚠ langchain-google-genai not installed. Skipping Gemini.")
        else:
            print("\n⚠ GOOGLE_API_KEY not set. Skipping Gemini evaluation.")
    
    # Summarize + save
    if results:
        compare_models(results)
        out_path = save_results(results, results_dir)
        print(f"\n✔ Results saved to: {out_path}")
    else:
        print("\n❌ No evaluation results to save.")


if __name__ == "__main__":
    main()
