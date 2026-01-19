"""Blueprint extraction API endpoint"""

import tempfile
import os
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.blueprint_extractor import extract_rooms_from_blueprint
from app.models.domain import BlueprintExtractionResult

router = APIRouter(prefix="/api/blueprint", tags=["blueprint"])

@router.post("/extract/", response_model=BlueprintExtractionResult)
async def extract_blueprint(
    file: UploadFile = File(..., description="Blueprint image (PNG/JPG) or PDF"),
    scale: Optional[float] = Form(None, description="Scale factor (default: 1.0 for 1:100)"),
    page_index: Optional[int] = Form(None, description="PDF page index (0-based). If None, extracts all pages combined.")
) -> BlueprintExtractionResult:
    """
    Extract room data from blueprint image using VLM.
    
    This is the preview-only - CSV pipeline remains ground truth.
    
    Args:
        file: Blueprint image (PNG, JPG) or PDF
        scale: Optional scale override (1.0 = 1:100 scale)
        page_index: Optional PDF page index (0-based). If None, all pages are combined vertically.
        
    Returns:
        BlueprintExtractionResult with extracted rooms and confidence scores
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
        # Extract rooms from blueprint (returns BlueprintExtractionResult directly)
        result = extract_rooms_from_blueprint(
            image_path=tmp_path,
            scale_override=scale,
            page_index=page_index
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