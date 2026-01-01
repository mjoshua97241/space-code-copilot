"""
Chat API endpoint: RAG-based Q&A for building code questions.

Uses hybrid retrieval (BM25 + Dense) to answer user questions about building codes with citations from source documents.

Pattern adapter from:
- app/api/issues.py: FASTAPI router pattern
- app/services/rule_extractor.py: RAG chain pattern
"""
from configparser import MAX_INTERPOLATION_DEPTH
from optparse import Option
from backend.app.services import vector_store
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path

from app.core.llm import get_llm, setup_llm_cache
from app.services.vector_store import VectorStore
from app.services.pdf_ingest import ingest_pdf

# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.

    Fields:
    - query: User's question about building codes.
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's question about building codes."
    )

class Citation(BaseModel):
    """
    Citation model for source references.

    Represents a reference to a source document that supports the answer.
    """
    source: str = Field(
        ..., description="Source document name (e.g. 'National-Building-Code')"
    )
    page: Optional[int] = Field(
        None, decription="Page number in source document"
    )
    section: Optional[str] = Field(
        None, description="Section number (e.g., '5.2.3')"
    )
    test: Optional[str] = Field(
        None, description="Relevant excerpt from source"
    )

class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.

    Fields:
    - answer: LLM-generated answer to the user's question
    - citation: List of source citations supporting the answer
    """
    answer: str = Field(
        ..., description="LLM-generated answer to the question"
    )
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of source citations"
    )


# ============================================================================
# API Router Setup
# ============================================================================

rounter = APIRouter(
    prefix="/api/chat",
    tags=["chat"] # Groups endpoint in API docs
)

# ============================================================================
# Vector Store Initialization (Singleton Pattern)
# ============================================================================

# Global vector store instance (initialized on first use)
_vector_store: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    """
    Get or create the global vectore store instance.

    This uses a singleton patter to avoid recreting the vector store on every request. The vector store is initialized lazily of first use.

    **Design decision**:
    - In-memory Qdrant means we need to re-index PDFs on each server restart
    - For MVP, this is acceptable. For production, use persistent Qdrant.

    Returns:
        VectoreStore instance with PDFs indexed
    """
    global _vector_store

    if vector_store is None:
        # Initialize vectore store
        _vector_store = VectorStore()

        # Index PDFs (for MVP, we index on startup)
        # In production, you might want to do this separately or cache it
        pdf_dir = Path(__file__).parent.parent / "data"
        pdf_files = list(pdf_dir.glob("*.pdf"))

        if pdf_files:
            print(f"Indexing {len(pdf_files)} PDF files...")
            for pdf_path in pdf_files:
                try:
                    chunks = ingest_pdf(str(pdf_path))
                    _vector_store.add_documents(chunks)
                    print(f"    ✓ Indexed {pdf_path.name} ({len(chunks)})")
                except Exception as e:
                    print(f"    ✗ Failed to index {pdf_path.name}: {e}")

            else:
                print("Warning: No PDF fiels found in app/data")
    return _vector_store

# ============================================================================
# LLM Cache Setup (Optional but Recommended)
# ============================================================================

# Setup LLM cache on module import (only once)
# This causes LLM responses to avoid redundant API calls
_setup_cache_done = False

if not _setup_cache_done:
    setup_llm_cache(cache_type="memory")
    _setup_cache_done = True

# ============================================================================
# POST /api/chat Endpoint
# ============================================================================