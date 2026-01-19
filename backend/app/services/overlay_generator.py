"""
Overlay generator service for dynamic bounding box overlays.

Uses OCR + text positioning to generate overlays from extracted room data.
Matches VLM-extracted room names to OCR text positions, then infers room boundaries.
"""

import re
import io
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass

# Image processing
try:
    from PIL import Image
    import fitz  # PyMuPDF
except ImportError:
    raise ImportError("Required packages missing. Install: pip install pillow PyMuPDF")

# OCR
try:
    import pytesseract
except ImportError:
    raise ImportError("pytesseract not installed. Install: pip install pytesseract")

# Optional: OpenCV for advanced boundary detection
try:
    import cv2
    import numpy as np
    OPENCV_AVAILABLE = True
except ImportError:
    OPENCV_AVAILABLE = False

# Fuzzy matching
from rapidfuzz import fuzz, process

# Project imports
from app.models.domain import Room, Overlay


@dataclass
class TextPosition:
    """Text position from OCR with coordinates."""
    text: str
    x: int
    y: int
    width: int
    height: int
    confidence: float = 0.0


def _load_image_for_ocr(image_path: Union[str, Path], page_index: Optional[int] = None) -> Image.Image:
    """
    Load image file for OCR processing.
    
    Handles PNG/JPG images and PDF files (extracts specific page or first page).
    Similar to blueprint_extractor._load_image_as_base64 but returns PIL Image.
    
    Args:
        image_path: Path to image or PDF file
        page_index: Optional page index (0-based) for PDFs. If None, uses first page.
    
    Returns:
        PIL Image object ready for OCR
    """
    image_path = Path(image_path)
    
    if not image_path.exists():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Handle PDF files
    if image_path.suffix.lower() == '.pdf':
        doc = fitz.open(str(image_path))
        if len(doc) == 0:
            raise ValueError(f"PDF has no pages: {image_path}")
        
        # Extract specific page or first page
        page_num = page_index if page_index is not None else 0
        if page_num < 0 or page_num >= len(doc):
            doc.close()
            raise ValueError(f"Page index {page_num} out of range (0-{len(doc)-1})")
        
        page = doc[page_num]
        mat = fitz.Matrix(2.0, 2.0)  # 2x zoom for better OCR
        pix = page.get_pixmap(matrix=mat)
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))
        doc.close()
        
        return img
    else:
        # Load regular image file (PNG, JPG, etc.)
        return Image.open(image_path)


def find_text_positions(image_path: Union[str, Path], page_index: Optional[int] = None) -> List[TextPosition]:
    """
    Extract text positions from blueprint image using OCR.
    
    Uses pytesseract to find all text with their pixel coordinates.
    
    Args:
        image_path: Path to blueprint image or PDF
        page_index: Optional page index for PDFs
    
    Returns:
        List of TextPosition objects with text and coordinates
    """
    # Load image
    img = _load_image_for_ocr(image_path, page_index)
    
    # Use pytesseract to get text with coordinates
    # image_to_data returns detailed information including coordinates
    try:
        ocr_data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as e:
        raise RuntimeError(f"OCR failed: {e}. Make sure Tesseract is installed.")
    
    text_positions = []
    
    # Process OCR results
    n_boxes = len(ocr_data['text'])
    for i in range(n_boxes):
        text = ocr_data['text'][i].strip()
        conf = float(ocr_data['conf'][i])
        
        # Skip empty text or low confidence
        if not text or conf < 0:
            continue
        
        # Get coordinates
        x = ocr_data['left'][i]
        y = ocr_data['top'][i]
        w = ocr_data['width'][i]
        h = ocr_data['height'][i]
        
        # Filter out very small text (likely noise)
        if w < 10 or h < 10:
            continue
        
        text_positions.append(TextPosition(
            text=text,
            x=x,
            y=y,
            width=w,
            height=h,
            confidence=conf / 100.0  # Convert to 0-1 scale
        ))
    
    return text_positions


def match_rooms_to_text(
    rooms: List[Room], 
    text_positions: List[TextPosition],
    fuzzy_threshold: int = 85
) -> Dict[str, TextPosition]:
    """
    Match VLM-extracted room names to OCR text positions using fuzzy matching.
    
    Uses rapidfuzz for fuzzy string matching to handle variations:
    - "Office / Bedroom" vs "Office/Bedroom" (space vs slash)
    - "T & B" vs "T&B" (spaces)
    - Case differences, minor spelling variations
    
    Args:
        rooms: List of extracted Room objects from VLM
        text_positions: List of text positions from OCR
        fuzzy_threshold: Minimum similarity score (0-100) for fuzzy match
    
    Returns:
        Dictionary mapping room_id -> TextPosition (matched text)
    """
    matches = {}
    
    # Create lookup for exact matches first (faster)
    text_by_exact = {
        text.text.lower().strip(): text 
        for text in text_positions
    }
    
    # Track which text positions have been matched
    matched_text_indices = set()
    
    # First pass: Try exact matches (case-insensitive, trimmed)
    for room in rooms:
        room_name_lower = room.name.lower().strip()
        
        if room_name_lower in text_by_exact:
            matches[room.id] = text_by_exact[room_name_lower]
            matched_text_indices.add(id(text_by_exact[room_name_lower]))
    
    # Second pass: Try fuzzy matching for unmatched rooms
    unmatched_rooms = [r for r in rooms if r.id not in matches]
    unmatched_texts = [
        t for t in text_positions 
        if id(t) not in matched_text_indices
    ]
    
    if unmatched_rooms and unmatched_texts:
        for room in unmatched_rooms:
            # Try fuzzy match
            best_match = process.extractOne(
                room.name,
                [t.text for t in unmatched_texts],
                scorer=fuzz.ratio,
                score_cutoff=fuzzy_threshold
            )
            
            if best_match:
                # Find the corresponding TextPosition
                matched_text = next(
                    t for t in unmatched_texts 
                    if t.text == best_match[0]
                )
                matches[room.id] = matched_text
                matched_text_indices.add(id(matched_text))
    
    return matches


def infer_room_boundaries(
    image_path: Union[str, Path],
    text_position: TextPosition,
    room: Room,
    use_opencv: bool = False
) -> Overlay:
    """
    Infer room boundaries from text position using heuristics.
    
    Searches for room boundaries (walls/outlines) near the text label.
    Uses simple heuristics by default, or OpenCV contour detection if available.
    
    Args:
        image_path: Path to blueprint image
        text_position: Position of room label text from OCR
        room: Room object (for metadata)
        use_opencv: Whether to use OpenCV for advanced boundary detection
    
    Returns:
        Overlay object with inferred boundaries (x, y, width, height)
    """
    # Load image
    img = _load_image_for_ocr(image_path)
    img_width, img_height = img.size
    
    if use_opencv and OPENCV_AVAILABLE:
        # Advanced: Use OpenCV for contour detection
        # Convert PIL to OpenCV format
        img_cv = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        
        # Edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours near text position
        # Search in a region around the text
        search_radius = max(text_position.width, text_position.height) * 3
        x_min = max(0, text_position.x - search_radius)
        y_min = max(0, text_position.y - search_radius)
        x_max = min(img_width, text_position.x + text_position.width + search_radius)
        y_max = min(img_height, text_position.y + text_position.height + search_radius)
        
        roi = edges[y_min:y_max, x_min:x_max]
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # Find largest contour (likely the room boundary)
            largest_contour = max(contours, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(largest_contour)
            
            # Adjust coordinates back to full image
            overlay_x = x + x_min
            overlay_y = y + y_min
            
            return Overlay(
                id=room.id,
                type="room",
                x=overlay_x,
                y=overlay_y,
                width=w,
                height=h,
                room_name=room.name,
                room_type=room.type
            )
    
    # Simple heuristic: Create overlay based on text position + estimated size
    # Assume room is roughly rectangular and extends from text position
    # Use area_m2 to estimate size (rough heuristic: 1 m² ≈ 1000 pixels at 1:100 scale)
    
    # Estimate room dimensions from area
    # Rough conversion: area_m2 * 1000 pixels per m² (for 1:100 scale)
    estimated_area_pixels = room.area_m2 * 1000
    
    # Estimate width/height (assume roughly square or slightly rectangular)
    # Use golden ratio for more realistic proportions
    estimated_width = int((estimated_area_pixels * 1.2) ** 0.5)
    estimated_height = int((estimated_area_pixels / 1.2) ** 0.5)
    
    # Position overlay: center text in overlay, extend outward
    overlay_x = max(0, text_position.x - estimated_width // 4)
    overlay_y = max(0, text_position.y - estimated_height // 4)
    overlay_width = min(img_width - overlay_x, estimated_width)
    overlay_height = min(img_height - overlay_y, estimated_height)
    
    # Ensure minimum size
    overlay_width = max(overlay_width, text_position.width * 2)
    overlay_height = max(overlay_height, text_position.height * 2)
    
    return Overlay(
        id=room.id,
        type="room",
        x=overlay_x,
        y=overlay_y,
        width=overlay_width,
        height=overlay_height,
        room_name=room.name,
        room_type=room.type
    )


def generate_overlays_from_blueprint(
    image_path: Union[str, Path],
    extracted_rooms: List[Room],
    page_index: Optional[int] = None,
    use_opencv: bool = False,
    fuzzy_threshold: int = 85
) -> List[Overlay]:
    """
    Generate overlays from blueprint image and extracted rooms.
    
    Main orchestrator function that:
    1. Uses OCR to find text positions
    2. Matches room names to text positions (fuzzy matching)
    3. Infers room boundaries for each matched room
    4. Returns list of Overlay objects
    
    Args:
        image_path: Path to blueprint image or PDF
        extracted_rooms: List of Room objects extracted by VLM
        page_index: Optional page index for PDFs
        use_opencv: Whether to use OpenCV for boundary detection (requires opencv-python)
        fuzzy_threshold: Minimum similarity score (0-100) for fuzzy matching
    
    Returns:
        List of Overlay objects with pixel coordinates
    
    Example:
        overlays = generate_overlays_from_blueprint(
            image_path="blueprint.pdf",
            extracted_rooms=result.rooms,
            use_opencv=True
        )
    """
    if not extracted_rooms:
        return []
    
    # Step 1: Find text positions using OCR
    try:
        text_positions = find_text_positions(image_path, page_index)
    except Exception as e:
        # If OCR fails, return empty list (graceful degradation)
        # Could log warning here
        return []
    
    if not text_positions:
        # No text found, return empty list
        return []
    
    # Step 2: Match room names to text positions
    room_to_text = match_rooms_to_text(
        extracted_rooms, 
        text_positions, 
        fuzzy_threshold=fuzzy_threshold
    )
    
    # Step 3: Infer boundaries for each matched room
    overlays = []
    for room in extracted_rooms:
        if room.id in room_to_text:
            text_pos = room_to_text[room.id]
            overlay = infer_room_boundaries(
                image_path,
                text_pos,
                room,
                use_opencv=use_opencv
            )
            overlays.append(overlay)
        # Note: Rooms without matched text won't get overlays
        # This is acceptable - not all rooms may have visible labels
    
    return overlays