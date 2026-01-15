"""
Blueprint extraction service using Vision LLM.

Extracts structured room data (name, type, area) from architectural blueprint images using semantic understanding and structured extraction.

Key capabilities:
- Reads room labels and classifies into types
- Associates scattered dimension annotations with rooms
- Calculates areas from dimensions using scale
- Produces structured JSON matching Room model schema
"""
from ast import Import
import base64
import io
import json
import os
from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import tempfile

# Import processing libraries
try:
    from PIL import image
    import fitz # PyMuPDF
except ImportError:
    raise ImportError(
        "Required packages missing. Install: pip install pillow PyMuPDF"
    )

# LangChain for vision LLM
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser

# Project imports
from app.core.llm import get_vision_llm
from app.models.domain import Room

def _load_image_as_base64(image_path: Union[str, Path]) -> str:
    """
    Load image file and convert to base64 string for VLM.
    
    Handles:
    - PNG/JPG images: Direct conversion
    - PDF files: Extracts first page as image
    
    Args:
        image_path: Path to image or PDF file
    
    Returns:
        Base64-encoded image string (data URI format)
        
    Explanation:
        Vision LLMs need images in base64 format. LangChain expects a data URI format: "data:image/png;base64,{base64_string}"
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Handle PDF files (extract first page as image)
    if image_path.suffix.lower() == '.pdf':
        doc = fitz.open(str(image_path))
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {image_path}")
        
        # Get first page
        page = doc[0]
        
        # Convert page to image (PNG format)
        # zoom=2.0 increases resolution for better VLM reading
        mat = fitz.Matrix(2.0, 2.0) # 2x zoom
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        doc.close()
    else:
        # Load regular image file (PNG, JPG, etc.)
        img = Image.open(image_path)
        
    # Convert PIL Image to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG") # Save as PNG for consistency
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
    
2. **Classify room types**: For each room, classify i into one of these types:
    - "bedroom" (sleeping rooms)
    - "living" (living room, family room)
    - "kitchen" (cooking areas)
    - "bathroom" (WC, toilet, shower)
    - "office" (work spaces, study rooms)
    - "meeting" (conference rooms, meeting spaces)
    - "corridor" (hallways, passages)
    - "storage" (closets, storage areas)
    - "other" (any other room type)
    
3. **Read dimensions**: Find dimension annotations scattered throughout the plan:
    - Look for numbers with units (e.g., "3.0", "4.0", "3.5m")
    - Dimension arrows typically point to room walls
    - Associate each dimension with the correct room
    
4. **Calculate areas**:
    - If dimensions are provided, calculate area: length x width (in meters)
    - If area is already labeled, use that value
    - Apply scale factor: {scale} (this means 1 unit on blueprint = {scale} meters in reality)
    - Convert all areas to square meters (m²)
    
5. **Assign floor level**: Determine which floor level this plan represents (default to 1 if unclear)

**Output format**: Return a JSON object with this exact structure:
{{
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
        LLM sometimes wrap JSON in``` blocks or add extra text.
        This function extracts the actual JSON content.
    """
    # Remove markdown code blocks if present
    text = response_text.strip()
    
    # Try to extract JSON from markdown code blocks
    if "" in text:
        # Extract content between and ```
        start = text.find("") + 7
        end = text.find("```", start)
        if end != -1:
            text = text[start:end].strip()
    elif "" in text:
        # Generated code block
        start = text.find("")
        end = text.find("", start)
        if end != -1:
            text = text[start:end].strip()
            # Parse JSON
            try:
                return json.loads(text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse LLM response as JSON: {e}\n"
                                 f"Response text: {response_text[:500]}"
                                 )
                
def validate_and_convert_rooms(
    raw_rooms: List[Dict[str, Any]]
) -> List[Room]:
    """
    Validate and convert raw room dictionaries to Room models.
    
    Validates:
        - Required fields: id, name, type, level, area_m2
        - Numeric ranges: area_m2 > 0, level >= 1
        - Type values: Must be valid room type
    
    Args:
        raw_rooms: List of room dictionaries from LLM
    
    Returns:
        List of validated Room Pydantic models
    
    Explanation:
        Pydantic models automatically validate data types and constraints.
        This ensures extracted rooms match the Room schema exactly.
    """
    validated_rooms = []
    for idx, room_dict in enumerate(raw_rooms):
        try:
            # Generate ID if missing
            if "id" not in room_dict or not room_dict["id"]:
                room_dict["id"] = f"R{100 + idx + 1}"
            
            # Ensure required fields exist
            if "name" not in room_dict:
                room_dict["name"] = f"Room {room_dict.get('id', idx + 1)}"
            
            if "type" not in room_dict:
                room_dict["type"] = "other"
                
            if "level" not in room_dict:
                room_dict["level"] = 1
                
            if "area_m2" not in room_dict:
                # Skip rooms without area (can't validated)
                continue
            
            # Validate area is positive
            if room_dict["area_m2"] <= 0:
                continue # Skip invalid areas
            
            # Create Room model (Pydantic validates automatically)
            room = Room(
                id=str(room_dict["id"]),
                name=str(room_dict["name"]),
                type=str(room_dict["type"]),
                level=int(room_dict["level"]),
                area_m2=float(room_dict["area_m2"])
            )
            
            validated_rooms.append(room)
        
        except Exception as e:
            # Skip invalid rooms, log error
            print(f"⚠️ Skipping invalid room {room_dict.get('id', idx)}: {e}")
            continue
        
        return validated_rooms

def calculate_confidence_scores(
    rooms: List[Room],
    raw_response: Dict[str, Any]
) -> Dict[str, float]:
    """
    Calculate confidence scores for extraction quality.
    
    Heuristics:
        - Overall: Based on number of rooms extracted and validation success
        - Name: All rooms have names (1.0) or some missing (lower)
        - Type: All rooms have valid types (1.0) or some "other" (lower)
        - Area: All rooms have areas (1.0) or some missing (lower)
    
    Args:
        rooms: Validated Room models
        raw_response: Raw JSON response from LLM
    
    Returns:
        Dictionary with confidence scores (0.0 to 1.0)
    
    Explanation:
        Simple heuristics for MVP. More sophisticated scoring can be added later (e.g., based on LLM confidence tokens, extraction quality metrics)
    """
    if not rooms:
        return {
            "overall": 0.0,
            "name_confidence": 0.0,
            "type_confidence": 0.0,
            "area_confidence": 0.0
        }
    total_rooms = len(rooms)
    
    # Name confidence: All rooms have non-empty names
    name_confidence = 1.0 if all(r.name and r.name.strip() for r in rooms) else 0.8
    
    # Type confidence: Fewer "other" types = higher confidence
    other_count = sum(1 for r in rooms if r.type == "other")
    type_confidence = 1.0 - (other_count / total_rooms * 0.3) # Penalize "other" types
    
    # Area confidence: All rooms have positive areas (already validated)
    area_confidence = 1.0
    
    # Overall: Weighted average
    overall = (
        name_confidence * 0.3 +
        type_confidence * 0.4 +
        area_confidence * 0.3
    )
    
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
    provider: Optional[str] = None
) -> Dict[str, Any]:
    """
    Extract room data from blueprint image using VLM semantic understanding.
    
    This is the main function that orchestrates the extraction pipeline:
        1. Load image (handle PDF by extracting first page)
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
    
    Returns:
        Dictionary with structure:
        {
            "rooms": List[Room],
            "confidence": {
                "overall": float,
                "name_confidence": float,
                "type_confidence": float,
                "area_confidence": float
            },
            "scale_used": float,
            "scale_source": str,
            "extraction_metadata": Dict[str, Any],
            "note": str
        }
        
        Note:
            Returns dict instead of BluePrintExtractionResult until models are created. Once ExtractionConfidence and BluePrintExtractionResult models exist, change return type and wrap result BluePrintExtractionResult.
    
    Example:
        result = extract_rooms_from_blueprint(
            image_path="blueprint.pdf",
            scale_override=1.0,
            model_name="gpt-4o"
        )
        rooms = result["rooms"] # List[Room]
        confidence = result["confidence"] # Dict[str, float]
    """
    
    # Step 1: Determine scale
    scale = scale_override if scale_override is not None else 1.0
    scale_scource = "user_input" if scale_override is not None else "default"
    
    # Step 2: Load iamge and convert to base64
    try:
        base64_image = _load_image_as_base64(image_path)
    except Exception as e:
        raise ValueError(f"Failed to load image: {e}")
    
    # Step 3: Build prompt
    prompt = _build_extraction_prompt(scale)
    
    # Step 4: Get vision LLM
    llm = get_vision_llm(provider=provider, model_name=model_name)
    
    # Step 5: Create message with image + text prompt
    # LangChain HumanMessage supports images via content list
    HumanMessage(
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
        raise RuntimeError(f"LLM call field: {e}")
    
    # Step 7: Parse JSON response
    try:
        parsed_response = _parse_llm_response(response_text)
    except Exception as e:
        raise ValueError(f"Failed to parse LLM response: {e}")
    
    # Step 8: Extract rooms from response
    raw_rooms = parsed_response.get("rooms", [])
    if not raw_rooms:
        raise ValueError("No rooms extracted from blueprint")
    
    # Step 9: Validate and convert to Room models
    validated_rooms = validate_and_convert_rooms(raw_rooms)
    if not validated_rooms:
        raise ValueError("No valid rooms extracted after validation")
    
    # Step 10: Calculate confidence scores
    confidence = calculate_confidence_scores(validated_rooms, parsed_response)
    
    # Step 11: Build result dictionary
    # TODO: Once ExtractionConfidence and BlueprintExtractionResult models exist, import them and return BlueprintExtractionResult instead of dict
    result = {
        "rooms": validated_rooms,
        "confidence": confidence,
        "scale_used": scale,
        "scale_source": scale_scource,
        "extraction_metadata": {
            "model_used": model_name,
            "provider": provider or os.getenv("VISION_LLM_PROVIDER", "openai"),
            "total_rooms_extracted": len(validated_rooms),
            "raw_rooms_count": len(raw_rooms)
        },
        "note": "Extraction is approximate. CSV pipeline remains ground truth."
    }
    
    return result