"""Blueprint extraction API endpoint"""

import tempfile
import os
from pathlib import Path
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from app.services.blueprint_extractor import extract_rooms_from_blueprint
from app.services.overlay_generator import generate_overlays_from_blueprint
from app.services.compliance_checker import check_compliance, get_compliance_summary
from app.models.domain import BlueprintExtractionResult, Issue

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

@router.post("/extract-and-check/", response_model=Dict[str, Any])
async def extract_and_check_compliance(
    file: UploadFile = File(..., description="Blueprint image (PNG/JPG) or PDF"),
    scale: Optional[float] = Form(None, description="Scale factor (default 1.0 for 1:100)"),
    page_index: Optional[int] = Form(None, description="PDF page index (0-based). If None, extracts all pages combined."),
    use_ocr_overlays: bool = Form(False, description="[DISABLED] Overlays are currently disabled - deferred to future recommendations"),
    use_opencv: bool = Form(False, description="[DISABLED] Overlays are currently disabled - deferred to future recommendations")
) -> Dict[str, Any]:
    """
    Extract rooms from blueprint, generate overlays, and check compliance.
    
    This endpoint combines:
    1. VLM-based room extraction
    2. Compliance checking against building code rules
    
    **Note**: Overlay generation is currently disabled (deferred to future recommendations).
    Overlays will be returned as empty list until frontend rendering is implemented.
    
    Args:
        file: Blueprint image (PNG, JPG) or PDF
        scale: Optional scale override (1.0 = 1:100 scale)
        page_index: Optional PDF page index (0-based). If None, all pages are combined
        use_ocr_overlays: Whether to use OCR as fallback for overlays (default: False, uses VLM overlays)
        use_opencv: Whether to use OpenCV for advanced boundary detection (requires opencv-python, only used if OCR overlays enabled)
        
    Returns:
        Dictionary with:
        - "extraction": BlueprintExtractionResult (overlays currently disabled, returns empty list)
        - "issues": List[Issue] - Compliance violations found
        - "summary": dict - Summary statistics of issues
    
    Example response:
        {
            "extraction": {
                "rooms": [...],
                "overlays": [...],
                "confidence": {...},
                ...
            },
            "issues": [
                {
                    "element_id": "r1",
                    "element_type": "room",
                    "rule_id": "min-area-bedroom",
                    "message": "Bedroom area (8.5 m²) is below minimum (9.0 m²)",
                    "code_ref": "IBC 1208.1",
                    "severity": "error"
                }
            ],
            "summary": {
                "total": 1,
                "by_element_type": {"room": 1, "door": 0},
                "by_severity": {"error": 1, "warning": 0}
            }
        }
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
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save upload file: {e}")
    
    try:
        # Step 1: Extract rooms from blueprint (VLM overlays are already included)
        result = extract_rooms_from_blueprint(
            image_path=tmp_path,
            scale_override=scale,
            page_index=page_index
        )
        
        # Step 2: Overlays disabled for now (deferred to future recommendations)
        # TODO: Re-enable overlay generation when frontend rendering is ready
        result.overlays = []  # Disable overlays - frontend rendering deferred
        
        # Step 3: Check compliance
        issues: List[Issue] = check_compliance(
            rooms=result.rooms,
            doors=[] # No doors extracted from blueprints yet
        )
        
        # Step 4: Generate summary
        summary = get_compliance_summary(issues)
        
        # Step 5: Return combined result
        return {
            "extraction": result,
            "issues": issues,
            "summary": summary
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {e}")
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)