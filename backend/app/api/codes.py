"""Building code PDF upload API endpoint"""

import tempfile
import os
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.pdf_ingest import ingest_pdf
from app.api.chat import get_vector_store

router = APIRouter(prefix="/api/codes", tags=["codes"])


@router.post("/upload/")
async def upload_building_code(
    file: UploadFile = File(..., description="Building code PDF file")
) -> dict:
    """
    Upload and index a building code PDF.
    
    Processes the PDF using the same pipeline as existing PDFs:
    1. Validates file type (PDF only)
    2. Saves to temporary file
    3. Ingests and chunks PDF
    4. Adds to vector store
    5. Returns metadata (filename, chunk count)
    
    Returns:
        {
            "success": true,
            "filename": "example.pdf",
            "chunks": 150,
            "message": "PDF indexed successfully"
        }
    """
    # Validate file type (PDF only)
    file_ext = Path(file.filename).suffix.lower() if file.filename else ""
    
    if file_ext != ".pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Only PDF files are allowed. Received: {file_ext or 'unknown file type'}"
        )
    
    # Save upload file temporarily
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to save uploaded file: {e}"
        )
    
    try:
        # Ingest and chunk the PDF
        chunks = ingest_pdf(tmp_path)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="PDF ingestion produced no chunks. The PDF may be empty or corrupted."
            )
        
        # Get vector store instance and add documents
        vector_store = get_vector_store()
        vector_store.add_documents(chunks)
        
        # Return success response with metadata
        return {
            "success": True,
            "filename": file.filename,
            "chunks": len(chunks),
            "message": "PDF indexed successfully"
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process PDF: {e}"
        )
    finally:
        # Clean up temp file
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
