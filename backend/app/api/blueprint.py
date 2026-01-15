"""Blueprint extraction API endpoint"""

from sys import prefix
import tempfile
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.blueprint_extractor import extract_rooms_from_blueprint
from app.models.domain import BluePrintExtractionResult, ExtractionConfidence

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])

@router.post("/extract", response_model=BluePrintExtractionResult)
async def extract_blueprint(
    file: UploadFile = File(..., description="Blueprint image (PNG/JPG) or PDF"),
    scale: Optional[float] = Form(None, description="Scale factor (default: 1.0 for 1:100)")
) -> BluePrintExtractionResult:
    """
    Extract room data from blueprint image using VLM.
    
    This is the preview-only - CSV pipeline remains ground truth.
    
    Args:
        file: Blueprint image (PNG, JPG) or PDF
        scale: Optional scale override (1.0 = 1:100 scale)
        
    Returns:
        BluePrintExtractionResult with extracted rooms and confidence scores
    """
    # Validate file type
    allowed_extensions = {".png", ".jpg", ".jpeg", ".pdf"}
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {file_ext}. Allowed: {', '.join(allowed_extensions)}"
        )
        
    # Save upload file temporarily
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {e}")
    
    try:
        # Extract rooms from blueprint
        result_dict = extract_rooms_from_blueprint(
            image_path=tmp_path,
            scale_override=scale
        )
        
        # Convert dict to BluePrintExtractionResult
        confidence = ExtractionConfidence(
            overall=result_dict["confidence"]["overall"],
            name_confidence=result_dict["confidence"]["name_confidence"],
            type_confidence=result_dict["confidence"]["type_confidence"],
            area_confidence=result_dict["confidence"]["area_confidence"]
        )
        
        result = BluePrintExtractionResult(
            rooms=result_dict["rooms"],
            confidence=confidence,
            scale_used=result_dict["scale_used"],
            scale_source=result_dict["scale_source"],
            extraction_metadata=result_dict["extraction_metadata"],
            note=result_dict["note"]
        )
        
        return result
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)