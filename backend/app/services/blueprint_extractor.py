"""
Blueprint extraction service using Vision LLM.

Extracts structured room data (name, type, area) from architectural blueprint images using semantic understanding and structured extraction.

Key capabilities:
- Reads room labels and classifies into types
- Associates scattered dimension annotations with rooms
- Calculates areas from dimensions using scale
- Produces structured JSON matching Room model schema
"""
import base64
import io
import json
import os
import re
from pathlib import Path
from typing import List, Optional, Union, Dict, Any

# Image processing libraries
try:
    from PIL import Image 
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError(
        "Required packages missing. Install: pip install pillow PyMuPDF"
    )

# LangChain for vision LLM
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

# Project imports
from app.core.llm import get_vision_llm
from app.models.domain import Room, ExtractionConfidence, BlueprintExtractionResult

VALID_ROOM_TYPES = {
    "bedroom", "living", "kitchen", "bathroom", "office", "meeting", "corridor", "storage", "other"
}

# Reasonable area bounds (in m²) for validation
MIN_ROOM_AREA_M2 = 2.0 # Minimum reasonable room area (e.g., small closet)
MAX_ROOM_AREA_M2 = 500.0 # Maximum reasonable room area (e.g., large hall)

def _load_image_as_base64(image_path: Union[str, Path], page_index: Optional[int] = None) -> str:
    """
    Load image file and convert to base64 string for VLM.
    
    Handles:
    - PNG/JPG images: Direct conversion
    - PDF files: Extracts all pages (or specific page if page_index provided) and combines them
    
    Args:
        image_path: Path to image or PDF file
        page_index: Optional page index (0-based) for PDFs. If None, extracts all pages.
                    For multi-page PDFs, pages are combined vertically into a single image.
    
    Returns:
        Base64-encoded image string (data URI format)
        
    Explanation:
        Vision LLMs need images in base64 format. LangChain expects a data URI format: "data:image/png;base64,{base64_string}"
        For multi-page PDFs, all pages are combined vertically to preserve the full blueprint context.
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Handle PDF files
    if image_path.suffix.lower() == '.pdf':
        doc = fitz.open(str(image_path))
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {image_path}")
        
        # Determine which pages to extract
        if page_index is not None:
            if page_index < 0 or page_index >= len(doc):
                doc.close()
                raise ValueError(f"Page index {page_index} out of range (0-{len(doc)-1})")
            pages_to_extract = [page_index]
        else:
            # Extract all pages
            pages_to_extract = list(range(len(doc)))
        
        # Convert pages to images and combine them
        page_images = []
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better VLM reading
        
        for page_num in pages_to_extract:
            page = doc[page_num]
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("png")
            page_img = Image.open(io.BytesIO(img_data))
            page_images.append(page_img)
        
        doc.close()
        
        # Combine pages vertically if multiple pages
        if len(page_images) == 1:
            img = page_images[0]
        else:
            # Calculate combined dimensions
            total_width = max(img.width for img in page_images)
            total_height = sum(img.height for img in page_images)
            
            # Create combined image
            combined_img = Image.new('RGB', (total_width, total_height), color='white')
            y_offset = 0
            for page_img in page_images:
                # Center page horizontally if narrower than total width
                x_offset = (total_width - page_img.width) // 2
                combined_img.paste(page_img, (x_offset, y_offset))
                y_offset += page_img.height
            
            img = combined_img
    else:
        # Load regular image file (PNG, JPG, etc.)
        img = Image.open(image_path)
    
    # Convert PIL Image to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")  # Save as PNG for consistency
    img_bytes = buffer.getvalue()
    
    # Encode to base64
    base64_str = base64.b64encode(img_bytes).decode('utf-8')
    
    # Return in data URI format (LangChain expects this)
    return f"data:image/png;base64,{base64_str}"

def _build_extraction_prompt(scale: float) -> str:
    """
    Build prompt for VLM emphasizing semantic understanding.
    
    This prompt instructs the VLM to:
    1. Read room labels (semantic extraction, not just OCR)
    2. Classify room types (office, bedroom, living, etc.)
    3. Associate dimensions with rooms (dimension-aware inference)
    4. Calculate areas using scale
    5. Output structured JSON
    
    Args:
        scale: Scale factor (e.g., 1.0 for 1:100 scale)
        
    Returns:
        Prompt string for VLM
    """
    return f"""Analyze this architectural blueprint image and extract all rooms with their properties.

**Your task:**
1. **Read room labels**: Identify all rooms by reading their labels (e.g., "Office 101", "Meeting Room", "Bedroom 1", "WC", "Kitchen").
    - Look for text labels inside or near room boundaries
    - Some labels may be scattered or abbreviated
    
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
    
    **Important abbreviations to recognize:**
    - "T&B" or "T & B" = bathroom (Toilet & Bath)
    - "WC" = bathroom (Water Closet)
    - "CR" = bathroom (Comfort Room)
    - "BR" = bedroom
    
3. **Read dimensions**: Find dimension annotations scattered throughout the plan:
    - Look for numbers with units (e.g., "3.0", "4.0", "3.5m")
    - Dimension arrows typically point to room walls
    - Associate each dimension with the correct room
    
4. **Calculate areas**:
    - If dimensions are provided, calculate area: length x width (in meters)
    - If area is already labeled, use that value
    - Apply scale factor: {scale} (this means 1 unit on blueprint = {scale} meters in reality)
    - Convert all areas to square meters (m²)
    
5. **Assign floor level**: Determine which floor level this plan represents by reading plan titles:
    - "GROUND FLOOR PLAN" or "GROUND FLOOR" or "FIRST FLOOR PLAN" = level 1
    - "SECOND FLOOR PLAN" or "2ND FLOOR PLAN" = level 2
    - "THIRD FLOOR PLAN" or "3RD FLOOR PLAN" = level 3
    - "FOURTH FLOOR PLAN" or "4TH FLOOR PLAN" = level 4
    - And so on for higher floors
    - Look for floor level labels in plan titles or headers
    - If no clear label is found, default to level 1

**Output format**: Return a JSON object with this exact structure:
{{
    "plan_title": "GROUND FLOOR PLAN",
    "rooms": [
        {{
            "id": "R101",
            "name": "Office 101",
            "type": "office",
            "level": 1,
            "area_m2": 12.0
        }},
        {{
            "id": "R102",
            "name": "Meeting Room",
            "type": "meeting",
            "level": 1,
            "area_m2": 25.5
        }}
    ]
}}

**Note**: Include "plan_title" field if you can read it from the blueprint (e.g., "GROUND FLOOR PLAN", "SECOND FLOOR PLAN"). This helps determine the correct floor level.

**Important**:
- Extract ALL rooms visible in the blueprint
- Use semantic understandng: "WC" = bathroom, "BR" = bedroom, etc.
- Associate dimensions correctly with rooms (dimension-aware interface)
- Ensure all areas are in square meters (m²)
- If a room's are cannot be determined, estimate based on dimensions or omit it
- Generate unique IDs (e.g., "R101", "R102") if not visible on the plan

Return ONLY valid JSON, no additional text.
"""

def _parse_llm_response(response_text: str) -> Dict[str, Any]:
    """
    Parse LLM response text into structured JSON.
    
    Handles:
    - JSON wrapped in markdown code blocks
    - Extra whitespace or text
    - Malformed JSON (with error handling)
    
    Args:
        response_text: Raw text response from LLM
    
    Returns:
        Parsed JSON dictionary
    
    Explanation:
        LLMs sometimes wrap JSON in ```json``` blocks or add extra text.
        This function extracts the actual JSON content.
    """
    # Remove markdown code blocks if present
    text = response_text.strip()
    
    # Try to extract JSON from markdown code blocks
    if "```json" in text:
        # Extract content between ```json and ```
        start = text.find("```json") + 7
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    elif "```" in text:
        # Generic code block
        start = text.find("```") + 3
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    
    # Parse JSON
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"Failed to parse LLM response as JSON: {e}\n"
            f"Response text: {response_text[:500]}"
        )
                
def _normalize_room_type(room_type: str, room_name: str = "") -> str:
    """
    Normalize room type by handling common abbreviations and variations.
    
    Args:
        room_type: Room type string from LLM
        room_name: Optional room name for additional context
    
    Returns:
        Normalized room type (must be in VALID_ROOM_TYPES)
    
    Explanation:
        Handles common abbreviations:
        - T&B, T & B, TB -> bathroom
        - WC, CR, Comfort Room -> bathroom
        - BR -> bedroom
        Also checks room name for additional context.
    """
    if not room_type:
        return "other"
    
    # Normalize: lowercase, strip, remove special chars
    normalized = room_type.lower().strip()
    name_lower = room_name.lower().strip() if room_name else ""
    
    # Bathroom variations
    bathroom_keywords = ["t&b", "t & b", "tb", "wc", "water closet", "cr", "comfort room", 
                         "toilet", "bath", "bathroom", "restroom", "lavatory"]
    if any(keyword in normalized or keyword in name_lower for keyword in bathroom_keywords):
        return "bathroom"
    
    # Bedroom variations
    bedroom_keywords = ["br", "bedroom", "bed room"]
    if any(keyword in normalized or keyword in name_lower for keyword in bedroom_keywords):
        return "bedroom"
    
    # Living room variations
    living_keywords = ["living", "family room", "familyroom", "dining", "living/dining"]
    if any(keyword in normalized or keyword in name_lower for keyword in living_keywords):
        return "living"
    
    # Kitchen variations
    kitchen_keywords = ["kitchen", "cooking"]
    if any(keyword in normalized or keyword in name_lower for keyword in kitchen_keywords):
        return "kitchen"
    
    # Office variations
    office_keywords = ["office", "study", "work"]
    if any(keyword in normalized or keyword in name_lower for keyword in office_keywords):
        return "office"
    
    # Meeting room variations
    meeting_keywords = ["meeting", "conference", "boardroom"]
    if any(keyword in normalized or keyword in name_lower for keyword in meeting_keywords):
        return "meeting"
    
    # Corridor variations
    corridor_keywords = ["corridor", "hallway", "hall", "passage"]
    if any(keyword in normalized or keyword in name_lower for keyword in corridor_keywords):
        return "corridor"
    
    # Storage variations
    storage_keywords = ["storage", "closet", "pantry"]
    if any(keyword in normalized or keyword in name_lower for keyword in storage_keywords):
        return "storage"
    
    # If it matches a valid type directly, return it
    if normalized in VALID_ROOM_TYPES:
        return normalized
    
    # Default to "other" if no match
    return "other"

def _normalize_floor_level(level: Any, plan_title: str = "") -> int:
    """
    Normalize floor level by parsing plan titles and labels.
    
    Args:
        level: Floor level from LLM (int, str, or None)
        plan_title: Optional plan title/header text for context
    
    Returns:
        Normalized floor level (1-based integer)
    
    Explanation:
        Handles common floor level labels:
        - "GROUND FLOOR PLAN" -> 1
        - "SECOND FLOOR PLAN" -> 2
        - "2ND FLOOR PLAN" -> 2
        - etc.
        Also validates numeric level values.
    """
    # First, try to parse level as integer
    if level is not None:
        try:
            level_int = int(level)
            if level_int >= 1:
                return level_int
        except (ValueError, TypeError):
            pass
    
    # If level is invalid or missing, try to infer from plan title
    if plan_title:
        title_upper = plan_title.upper()
        
        # Ground/First floor
        if any(keyword in title_upper for keyword in ["GROUND FLOOR", "GROUND", "FIRST FLOOR", "1ST FLOOR"]):
            return 1
        
        # Second floor
        if any(keyword in title_upper for keyword in ["SECOND FLOOR", "2ND FLOOR", "2ND"]):
            return 2
        
        # Third floor
        if any(keyword in title_upper for keyword in ["THIRD FLOOR", "3RD FLOOR", "3RD"]):
            return 3
        
        # Fourth floor
        if any(keyword in title_upper for keyword in ["FOURTH FLOOR", "4TH FLOOR", "4TH"]):
            return 4
        
        # Fifth floor
        if any(keyword in title_upper for keyword in ["FIFTH FLOOR", "5TH FLOOR", "5TH"]):
            return 5
        
        # Try to extract number from title (e.g., "FLOOR 2", "LEVEL 3")
        floor_match = re.search(r'(?:FLOOR|LEVEL|FL)\s*(\d+)', title_upper)
        if floor_match:
            try:
                return int(floor_match.group(1))
            except ValueError:
                pass
    
    # Default to level 1 if nothing found
    return 1

def _validate_and_convert_rooms(
    raw_rooms: List[Dict[str, Any]],
    plan_title: str = ""
) -> List[Room]:
    """
    Validate and convert raw room dictionaries to Room models.
    
    Validates:
        - Required fields: id, name, type, level, area_m2
        - Numeric ranges: 
            - area_m2: 2.0 to 500.0 m² (reasonable bounds)
            - level: >= 1 (enforced by Pydantic)
        - Type values: Must be in VALID_ROOM_TYPES set
        - Name validation: Non-empty, not just whitespace
    
    Args:
        raw_rooms: List of room dictionaries from LLM
        plan_title: Optional plan title/header text for floor level inference
    
    Returns:
        List of validated Room Pydantic models
    
    Explanation:
        This function performs multi-layer validation:
        1. Field presence check (required fields exist)
        2. Type validation (room type is in allowed set)
        3. Range validation (area is within reasonable bounds)
        4. Pydantic validation (automatic type conversion and constraint checking)
        
        Rooms that fail validation are skipped (not included in result).
        This ensures only valid rooms proceed to confidence scoring.
    """
    validated_rooms = []
    for idx, room_dict in enumerate(raw_rooms):
        try:
            # Step 1: Generate ID if missing
            if "id" not in room_dict or not room_dict["id"]:
                room_dict["id"] = f"R{100 + idx + 1}"
            
            # Step 2: Validate and set name
            if "name" not in room_dict or not room_dict.get("name", "").strip():
                # Generate default name if missing or empty
                room_dict["name"] = f"Room {room_dict.get('id', idx + 1)}"
            else:
                # Ensure name is not just whitespace
                room_dict["name"] = str(room_dict["name"]).strip()
            
            # Step 3: Normalize and validate room type
            room_type_raw = room_dict.get("type", "")
            room_name = room_dict.get("name", "")
            room_dict["type"] = _normalize_room_type(room_type_raw, room_name)
            
            # Ensure normalized type is in valid set (should always be after normalization)
            if room_dict["type"] not in VALID_ROOM_TYPES:
                room_dict["type"] = "other"
            
            # Step 4: Normalize and validate level
            level_raw = room_dict.get("level", None)
            room_dict["level"] = _normalize_floor_level(level_raw, plan_title)
                
            # Step 5: Validate area_m2 (CRITICAL - skip if invalid)
            if "area_m2" not in room_dict:
                # Skip rooms without area (can't validate)
                continue
            
            try:
                area = float(room_dict["area_m2"])
            except (ValueError, TypeError):
                # Skip rooms with non-numeric area
                continue
            
            # Range validation: area must be within reasonable bounds
            if area < MIN_ROOM_AREA_M2:
                # Too small - likely measurement error
                continue
            if area > MAX_ROOM_AREA_M2:
                # Too large - likely measurement error or unit confusion
                continue
            
            # Step 6: Create Room model (Pydantic validates automatically)
            # Pydantic will enforce:
            #   - level >= 1 (ge=1 constraint)
            #   - area_m2 > 0 (gt=0 constraint)
            #   - Type conversion (str, int, float)
            
            room = Room(
                id=str(room_dict["id"]),
                name=str(room_dict["name"]),
                type=str(room_dict["type"]),
                level=int(room_dict["level"]),
                area_m2=float(area)
            )
            validated_rooms.append(room)
            
        except Exception as e:
            # Skip invalid rooms, log error for debugging
            print(f"⚠ Skipping invalid room {room_dict.get('id', idx)}: {e}")
            continue
    
    return validated_rooms

def _calculate_confidence_scores(
    rooms: List[Room],
    raw_response: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate confidence scores for extraction quality.
    
    Enhanced heuristics:
        - Overall: Weighted combination of all sub-scores
        - Name confidence: Based on name quality (non-empty, not generic)
        - Type confidence: Based on type classification accuracy (fewer "other" = better)
        - Area confidence: Based on area reasonableness and consistency
    
    Args:
        rooms: Validated Room models (already passed validation)
        raw_response: Raw JSON response from LLM (for metadata)
    
    Returns:
        Dictionary with confidence scores (0.0 to 1.0):
        {
            "overall": float,
            "name_confidence": float,
            "type_confidence": float,
            "area_confidence": float,
        }
    
    Explanation:
        Confidence scoring uses heuristics because:
        1. LLMs don't always provide confidence tokens
        2. We can infer quality from extraction patterns
        
        Scoring factors:
        - Name quality: Generic names ("Room 1") = lower confidence
        - Type accuracy: More "other" types = lower confidence (LLM couldn't classify)
        - Area reasonableness: Area near bounds = lower confidence (might be errors)
        - Extraction completeness: More rooms extracted = higher confidence (if reasonable)
    """
    if not rooms:
        # No rooms extracted = zero confidence
        return {
            "overall": 0.0,
            "name_confidence": 0.0,
            "type_confidence": 0.0,
            "area_confidence": 0.0,
        }
    total_rooms = len(rooms)
    
    # ============================================================
    # Name Confidence Calculation
    # ============================================================
    # Check if names are generic (e.g., "Room 1", "Room 2")
    generic_name_patterns = ["room", "r", "space"]
    generic_count = 0
    
    for room in rooms:
        name_lower = room.name.lower().strip()
        # Check if name matches generic pattern
        is_generic = any(
            name_lower.startswith(pattern) and (len(name_lower) <= len(pattern) + 3) # "Room 1" = 6 chars
            for pattern in generic_name_patterns
        )
        if is_generic:
            generic_count += 1

    # Name confidence: Lower if many generic names
    # Formula: 1.0 if all specific, 0.7 if all generic
    name_confidence = 1.0 - (generic_count / total_rooms * 0.3)
    name_confidence = max(0.7, name_confidence)  # Floor at 0.7 (even generic names are extracted)
    
    # ============================================================
    # Type Confidence Calculation
    # ============================================================
    # Count "other" types (LLM couldn't classify)
    other_count = sum(1 for r in rooms if r.type == "other")
    
    # Type confidence: Penalize "other" types
    # Formula: 1.0 if no "other", 0.6 if all "other"
    type_confidence = 1.0 - (other_count / total_rooms * 0.4)
    type_confidence = max(0.6, type_confidence) # Floor at 0.6
    
    # ============================================================
    # Area Confidence Calculation
    # ============================================================
    # Check if areas are reasonable (not near bounds)
    # Areas near MIN or MAX might indicate measurement errors
    near_min_count = sum(1 for r in rooms if r.area_m2 < MIN_ROOM_AREA_M2 * 1.5)
    near_max_count = sum(1 for r in rooms if r.area_m2 > MAX_ROOM_AREA_M2 * 0.8)
    
    # Area confidence: Lower if many areas near bounds
    # Formula: 1.0 if all areas in middle range, 0.8 if many near bounds
    area_penalty = (near_min_count + near_max_count) / total_rooms * 0.2
    area_confidence = 1.0 - area_penalty
    area_confidence = max(0.8, area_confidence) # Floor at 0.8 (areas passed validation)
    
    # Additional check: Area consistency
    # If all rooms have very similar areas, might indicate extraction issue
    if total_rooms > 1:
        areas = [r.area_m2 for r in rooms]
        area_variance = max(areas) / min(areas) if min(areas) > 0 else 1.0
        if area_variance < 1.2:  # All areas within 20% of each other
            area_confidence *= 0.9  # Slight penalty for suspicious uniformity

    # ============================================================
    # Overall Confidence Calculation
    # ============================================================
    # Weighted average of all sub-scores
    # Weights reflect importance:
    #   - Type (40%): Most important (affects compliance checking)
    #   - Area (30%): Important (affects compliance checking)
    #   - Name (30%): Less critical (mainly for display)
    overall = (
        name_confidence * 0.3 + 
        type_confidence * 0.4 +
        area_confidence * 0.3
    )
    
    # Clamp to [0.0, 1.0] (safety check)
    overall = max(0.0, min(1.0, overall))
    
    return {
        "overall": overall,
        "name_confidence": name_confidence,
        "type_confidence": type_confidence,
        "area_confidence": area_confidence
    }


def extract_rooms_from_blueprint(
    image_path: Union[str, Path],
    scale_override: Optional[float] = None,
    model_name: str = "gpt-4o",
    provider: Optional[str] = None,
    page_index: Optional[int] = None
) -> BlueprintExtractionResult:
    """
    Extract room data from blueprint image using VLM semantic understanding.
    
    This is the main function that orchestrates the extraction pipeline:
        1. Load image (handle PDF by extracting all pages or specific page)
        2. Convert to base64 for VLM
        3. Build prompt emphasizing semantic understanding
        4. Call vision LLM
        5. Parse JSON response
        6. Validate against Room model
        7. Calculate confidence scores
        8. Return extraction result
    
    Args:
        image_path: Path to blueprint image (PNG/JPG) or PDF
        scale_override: Optional scale factor (default: 1.0 for 1:100 scale)
            - 1.0 = 1:100 scale (1 unit on blueprint = 1 meter)
            - 0.5 = 1:200 scale (1 unit on blueprint = 0.5 meters)
        model_name: VLM model to use ("gpt-4o", "gemini-1.5-flash". etc.)
        provider: LLM provider ("openai", "gemini") - defaults to env var
        page_index: Optional page index (0-based) for PDFs. If None, extracts all pages.
                    For multi-page PDFs, all pages are combined vertically into a single image.
    
    Returns:
        BlueprintExtractionResult with validated rooms and confidence scores.
    
    Example:
        result = extract_rooms_from_blueprint(
            image_path="blueprint.pdf",
            scale_override=1.0,
            model_name="gpt-4o"
        )
        rooms = result.rooms  # List[Room]
        confidence = result.confidence  # ExtractionConfidence
    """
    
    # Step 1: Determine scale
    scale = scale_override if scale_override is not None else 1.0
    scale_source = "user_input" if scale_override is not None else "default"
    
    # Step 2: Load image and convert to base64
    try:
        base64_image = _load_image_as_base64(image_path, page_index=page_index)
    except Exception as e:
        raise ValueError(f"Failed to load image: {e}")
    
    # Step 3: Build prompt
    prompt = _build_extraction_prompt(scale)
    
    # Step 4: Get vision LLM
    llm = get_vision_llm(provider=provider, model_name=model_name)
    
    # Step 5: Create message with image + text prompt
    # LangChain HumanMessage supports images via content list
    message = HumanMessage(
        content=[
            {
                "type": "image_url",
                "image_url": {
                    "url": base64_image
                }
            },
            {
                "type": "text",
                "text": prompt
            }
        ]
    )
    
    # Step 6: Call LLM
    try:
        response = llm.invoke([message])
        response_text = response.content
    except Exception as e:
        raise RuntimeError(f"LLM call failed: {e}")
    
    # Step 7: Parse JSON response
    try:
        parsed_response = _parse_llm_response(response_text)
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {e}")
    
    # Step 8: Extract rooms and plan metadata from response
    raw_rooms = parsed_response.get("rooms", [])
    if not raw_rooms:
        raise ValueError("No rooms extracted from blueprint")
    
    # Extract plan title if available (for floor level inference)
    plan_title = parsed_response.get("plan_title", "") or parsed_response.get("title", "")
    
    # Step 9: Validate and convert to Room models
    validated_rooms = _validate_and_convert_rooms(raw_rooms, plan_title=plan_title)
    if not validated_rooms:
        raise ValueError("No valid rooms extracted after validation")
    
    # Step 10: Calculate confidence scores
    confidence = _calculate_confidence_scores(validated_rooms, parsed_response)
    
    # Step 11: Build result using Pydantic models
    confidence_obj = ExtractionConfidence(**confidence)
    
    result = BlueprintExtractionResult(
        rooms=validated_rooms,
        confidence=confidence_obj,
        scale_used=scale,
        scale_source=scale_source,
        extraction_metadata={
            "model_used": model_name,
            "provider": provider or os.getenv("VISION_LLM_PROVIDER", "openai"),
            "total_rooms_extracted": len(validated_rooms),
            "raw_rooms_count": len(raw_rooms)
        },
        note="Extraction is approximate. CSV pipeline remains ground truth."
    )
    
    return result