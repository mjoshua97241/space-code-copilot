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
    import os
    # Configure TESSDATA_PREFIX for Tesseract
    # Try common tessdata locations
    tessdata_paths = [
        "/usr/share/tesseract-ocr/5/tessdata",
        "/usr/share/tesseract-ocr/4.00/tessdata",
        "/usr/share/tesseract-ocr/tessdata",
        "/snap/tesseract/current/usr/share/tesseract-ocr/5/tessdata",
        "/snap/tesseract/current/usr/share/tesseract-ocr/tessdata",
    ]
    tessdata_found = False
    for path in tessdata_paths:
        eng_file = os.path.join(path, "eng.traineddata")
        if os.path.exists(path) and os.path.exists(eng_file):
            os.environ["TESSDATA_PREFIX"] = path
            tessdata_found = True
            break
    
    # If tessdata not found, try to get it from pytesseract's config
    if not tessdata_found:
        try:
            # Try to get tessdata path from pytesseract
            tessdata_config = pytesseract.pytesseract.tesseract_cmd
            # This might help, but we'll also check if we can download tessdata
            pass
        except:
            pass
    
    # Log tessdata configuration
    import logging
    logger = logging.getLogger(__name__)
    if tessdata_found:
        logger.info(f"TESSDATA_PREFIX set to: {os.environ.get('TESSDATA_PREFIX')}")
    else:
        logger.warning("TESSDATA_PREFIX not found. Tesseract may not work. "
                      "Install language pack: sudo apt install tesseract-ocr-eng")
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
    Applies preprocessing to improve OCR accuracy for blueprint text.
    
    Args:
        image_path: Path to blueprint image or PDF
        page_index: Optional page index for PDFs
    
    Returns:
        List of TextPosition objects with text and coordinates
    """
    # Load image
    img = _load_image_for_ocr(image_path, page_index)
    
    # Preprocess image for better OCR
    # Convert to grayscale if needed
    if img.mode != 'L':
        img = img.convert('L')
    
    # Enhance contrast (helps with blueprint text)
    from PIL import ImageEnhance
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.5)  # Increase contrast by 50%
    
    # Use pytesseract to get text with coordinates
    # Try different OCR modes for better results
    # PSM 6 = Assume a single uniform block of text (good for labels)
    # PSM 11 = Sparse text (good for scattered labels)
    ocr_configs = [
        '--psm 6',  # Single uniform block
        '--psm 11',  # Sparse text
        '--psm 12',  # Sparse text with OSD
    ]
    
    all_text_positions = []
    
    for config in ocr_configs:
        try:
            ocr_data = pytesseract.image_to_data(
                img, 
                output_type=pytesseract.Output.DICT,
                config=config
            )
            
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
                
                # Filter out pure numbers/measurements (likely dimensions, not room labels)
                # Room labels typically contain letters
                if text.replace('.', '').replace(',', '').replace(' ', '').isdigit():
                    continue
                
                # Filter out very short single characters (unless they're part of a word)
                if len(text) == 1 and text.isalpha() and text not in ['A', 'B', 'C', 'D', 'E']:
                    continue
                
                all_text_positions.append(TextPosition(
                    text=text,
                    x=x,
                    y=y,
                    width=w,
                    height=h,
                    confidence=conf / 100.0  # Convert to 0-1 scale
                ))
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"OCR config {config} failed: {e}")
            continue
    
    # Deduplicate text positions (same text at same position)
    seen = set()
    text_positions = []
    for tp in all_text_positions:
        key = (tp.text.lower(), tp.x, tp.y)
        if key not in seen:
            seen.add(key)
            text_positions.append(tp)
    
    return text_positions


def match_rooms_to_text(
    rooms: List[Room], 
    text_positions: List[TextPosition],
    fuzzy_threshold: int = 85
) -> Dict[str, TextPosition]:
    """
    Match VLM-extracted room names to OCR text positions using fuzzy matching.
    
    Uses rapidfuzz for fuzzy string matching to handle variations.
    Prioritizes longer, more complete matches over short fragments.
    
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
    # Filter out very short text fragments that are likely not room labels
    # Room labels are typically at least 3-4 characters
    meaningful_texts = [
        t for t in text_positions 
        if id(t) not in matched_text_indices
        and len(t.text.strip()) >= 3  # Minimum length for room labels
    ]
    
    unmatched_rooms = [r for r in rooms if r.id not in matches]
    
    if unmatched_rooms and meaningful_texts:
        for room in unmatched_rooms:
            room_name_clean = room.name.upper().strip()
            room_name_lower = room.name.lower().strip()
            
            # Score all potential matches
            candidates = []
            for text_pos in meaningful_texts:
                text_upper = text_pos.text.upper().strip()
                text_lower = text_pos.text.lower().strip()
                
                # Calculate multiple similarity scores
                exact_score = 100 if room_name_lower == text_lower else 0
                partial_score = fuzz.partial_ratio(room_name_clean, text_upper)
                token_score = fuzz.token_sort_ratio(room_name_clean, text_upper)
                ratio_score = fuzz.ratio(room_name_clean, text_upper)
                
                # Weighted combination favoring longer, more complete matches
                # Penalize very short matches (likely fragments)
                length_penalty = 1.0 if len(text_upper) >= len(room_name_clean) * 0.5 else 0.7
                
                # Best score is max of all methods
                best_score = max(exact_score, partial_score, token_score, ratio_score) * length_penalty
                
                # Prefer matches where text length is similar to room name length
                length_similarity = 1.0 - abs(len(text_upper) - len(room_name_clean)) / max(len(room_name_clean), 1)
                final_score = best_score * (0.7 + 0.3 * length_similarity)
                
                if final_score >= fuzzy_threshold:
                    candidates.append((text_pos, final_score))
            
            # Choose best match if any meet threshold
            if candidates:
                # Sort by score (descending) and take best
                candidates.sort(key=lambda x: x[1], reverse=True)
                best_text_pos, best_score = candidates[0]
                
                # Additional validation: if match is very short, require higher score
                if len(best_text_pos.text.strip()) < len(room_name_clean) * 0.6:
                    if best_score < fuzzy_threshold + 10:  # Require higher threshold for short matches
                        continue
                
                matches[room.id] = best_text_pos
                matched_text_indices.add(id(best_text_pos))
                
                import logging
                logger = logging.getLogger(__name__)
                logger.debug(f"Matched '{room.name}' to OCR text '{best_text_pos.text}' (score: {best_score:.1f})")
    
    return matches


def infer_room_boundaries(
    image_path: Union[str, Path],
    text_position: TextPosition,
    room: Room,
    use_opencv: bool = False
) -> Overlay:
    """
    Create overlay from text position (highlighting room name only).
    
    Instead of inferring full room boundaries, this creates a small bounding box
    around the detected room label text with some padding for visibility.
    
    Args:
        image_path: Path to blueprint image (used for image dimensions)
        text_position: Position of room label text from OCR
        room: Room object (for metadata)
        use_opencv: Not used (kept for API compatibility)
    
    Returns:
        Overlay object with text position coordinates (with padding)
    """
    # Load image to get dimensions (for bounds checking)
    img = _load_image_for_ocr(image_path)
    img_width, img_height = img.size
    
    # Add padding around text for better visibility
    # Padding is proportional to text size
    padding_x = max(5, text_position.width * 0.2)  # 20% padding, min 5px
    padding_y = max(3, text_position.height * 0.3)  # 30% padding, min 3px
    
    # Create overlay centered on text position with padding
    overlay_x = max(0, int(text_position.x - padding_x))
    overlay_y = max(0, int(text_position.y - padding_y))
    overlay_width = min(
        img_width - overlay_x,
        int(text_position.width + (padding_x * 2))
    )
    overlay_height = min(
        img_height - overlay_y,
        int(text_position.height + (padding_y * 2))
    )
    
    # Ensure minimum size for visibility
    overlay_width = max(overlay_width, 30)
    overlay_height = max(overlay_height, 15)
    
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        text_positions = find_text_positions(image_path, page_index)
        logger.info(f"OCR found {len(text_positions)} text positions")
    except Exception as e:
        # If OCR fails, return empty list (graceful degradation)
        logger.error(f"OCR failed: {e}", exc_info=True)
        return []
    
    if not text_positions:
        # No text found, return empty list
        logger.warning(f"No text found in image {image_path}")
        return []
    
    # Step 2: Match room names to text positions
    room_to_text = match_rooms_to_text(
        extracted_rooms, 
        text_positions, 
        fuzzy_threshold=fuzzy_threshold
    )
    
    logger.info(f"Matched {len(room_to_text)}/{len(extracted_rooms)} rooms to text positions")
    if len(room_to_text) > 0:
        for room_id, text_pos in room_to_text.items():
            room = next(r for r in extracted_rooms if r.id == room_id)
            logger.info(f"  Room '{room.name}' -> OCR text '{text_pos.text}' at ({text_pos.x}, {text_pos.y})")
    if len(room_to_text) == 0:
        logger.warning(f"No room names matched to OCR text. "
                      f"Extracted rooms: {[r.name for r in extracted_rooms]}, "
                      f"OCR texts: {[t.text for t in text_positions[:10]]}")  # Show first 10 OCR texts
    
    # Step 3: Infer boundaries for each matched room
    overlays = []
    for room in extracted_rooms:
        if room.id in room_to_text:
            text_pos = room_to_text[room.id]
            try:
                overlay = infer_room_boundaries(
                    image_path,
                    text_pos,
                    room,
                    use_opencv=use_opencv
                )
                overlays.append(overlay)
            except Exception as e:
                logger.warning(f"Failed to infer boundaries for room {room.id} ({room.name}): {e}")
        # Note: Rooms without matched text won't get overlays
        # This is acceptable - not all rooms may have visible labels
    
    logger.info(f"Generated {len(overlays)} overlays")
    return overlays