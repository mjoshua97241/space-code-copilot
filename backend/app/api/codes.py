"""Building code PDF upload API endpoint"""

import tempfile
import os
import shutil
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
    5. Saves to persistent storage (app/data/uploads/) for compliance checking
    6. Returns metadata (filename, chunk count)
    
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
    
    # Prepare persistent storage directory
    data_dir = Path(__file__).parent.parent / "data"
    uploads_dir = data_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine final filename (handle duplicates by appending number)
    original_filename = file.filename or "uploaded.pdf"
    final_path = uploads_dir / original_filename
    
    # Handle duplicate filenames
    counter = 1
    while final_path.exists():
        stem = Path(original_filename).stem
        suffix = Path(original_filename).suffix
        final_path = uploads_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    try:
        # Ingest and chunk the PDF
        chunks = ingest_pdf(tmp_path)
        
        if not chunks:
            raise HTTPException(
                status_code=400,
                detail="PDF ingestion produced no chunks. The PDF may be empty or corrupted."
            )
        
        # Update source metadata to use the actual filename (not temp file name)
        # The ingest_pdf function uses Path(file_path).stem, which would be the temp filename
        # We need to override it with the actual uploaded filename
        actual_source_name = Path(final_path).stem  # Use the saved filename (handles duplicates)
        for chunk in chunks:
            chunk.metadata["source"] = actual_source_name
        
        # Get vector store instance and add documents
        vector_store = get_vector_store()
        vector_store.add_documents(chunks)
        
        # Save to persistent storage for compliance checking
        # This ensures uploaded PDFs are available for rule extraction
        shutil.copy2(tmp_path, final_path)
        
        # Return success response with metadata
        return {
            "success": True,
            "filename": final_path.name,  # Return actual saved filename
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
