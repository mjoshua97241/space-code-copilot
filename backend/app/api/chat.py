"""
Chat API endpoint: RAG-based Q&A for building code questions.

Uses hybrid retrieval (BM25 + Dense) to answer user questions about building codes
with citations from source documents.

Pattern adapted from:
- app/api/issues.py: FastAPI router pattern
- app/services/rule_extractor.py: RAG chain pattern
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from pathlib import Path
import os

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

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
    - query: User's question about building codes
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's question about building codes"
    )


class Citation(BaseModel):
    """
    Citation model for source references.
    
    Represents a reference to a source document that supports the answer.
    """
    source: str = Field(..., description="Source document name (e.g., 'National-Building-Code')")
    page: Optional[str] = Field(None, description="Page number in source document (e.g., '31 (PDF page)' or '20 (document page)')")
    section: Optional[str] = Field(None, description="Section number (e.g., '5.2.3')")
    text: Optional[str] = Field(None, description="Relevant excerpt from source")


class ChatResponse(BaseModel):
    """
    Response model for chat endpoint.
    
    Fields:
    - answer: LLM-generated answer to the user's question
    - citations: List of source citations supporting the answer
    """
    answer: str = Field(..., description="LLM-generated answer to the question")
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of source citations"
    )


# ============================================================================
# API Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"]  # Groups endpoints in API docs
)


# ============================================================================
# Vector Store Initialization (Singleton Pattern)
# ============================================================================

# Global vector store instance (initialized on first use)
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create the global vector store instance.
    
    This uses a singleton pattern to avoid recreating the vector store
    on every request. The vector store is initialized lazily on first use.
    
    **Design decision**: 
    - In-memory Qdrant means we need to re-index PDFs on each server restart
    - For MVP, this is acceptable. For production, use persistent Qdrant.
    
    Returns:
        VectorStore instance with PDFs indexed
    """
    global _vector_store
    
    if _vector_store is None:
        # Initialize vector store
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
                    print(f"  ✓ Indexed {pdf_path.name} ({len(chunks)} chunks)")
                except Exception as e:
                    print(f"  ✗ Failed to index {pdf_path.name}: {e}")
        else:
            print("Warning: No PDF files found in app/data/")
    
    return _vector_store


# ============================================================================
# LLM Cache Setup (Optional but Recommended)
# ============================================================================

# Setup LLM cache on module import (only once)
# This caches LLM responses to avoid redundant API calls
_setup_cache_done = False

if not _setup_cache_done:
    setup_llm_cache(cache_type="memory")  # Use "sqlite" for production
    _setup_cache_done = True


# ============================================================================
# Helper Functions
# ============================================================================

def _fix_citations_in_answer(answer: str, retrieved_docs: list) -> str:
    """
    Post-process LLM answer to fix citations that are missing page type indicators.
    
    Finds citations in format [Source: ..., Page: X, ...] and adds "(PDF page)" or "(document page)"
    by looking up the actual page type from retrieved documents.
    
    Args:
        answer: LLM-generated answer text
        retrieved_docs: List of retrieved documents with metadata
    
    Returns:
        Answer text with corrected citations
    """
    import re
    
    # Create a map of (source, page_number) -> page_type
    page_type_map = {}
    for doc in retrieved_docs:
        source = doc.metadata.get("source", "Unknown")
        page_document = doc.metadata.get("page_document")
        page_pdf = doc.metadata.get("page_pdf")
        
        # Map both PDF and document pages
        if page_pdf:
            page_type_map[(source, str(page_pdf))] = "PDF page"
        if page_document:
            page_type_map[(source, str(page_document))] = "document page"
    
    # Pattern to find citations: [Source: Name, Page X, Section: Y] or [Source: Name, Page: X, Section: Y]
    # Handles both "Page X" and "Page: X" formats
    citation_pattern = r'\[Source:\s*([^,]+),\s*Page:?\s*(\d+)(?:\s*\([^)]+\))?(?:\s*,\s*Section:\s*([^\]]+))?\]'
    
    def replace_citation(match):
        source = match.group(1).strip()
        page_num = match.group(2).strip()
        section = match.group(3).strip() if match.group(3) else None
        
        # Check if citation already has page type
        if "(PDF page)" in match.group(0) or "(document page)" in match.group(0):
            return match.group(0)  # Already has type, don't change
        
        # Look up page type from map
        page_type = page_type_map.get((source, page_num))
        
        if page_type:
            # Reconstruct citation with page type
            citation = f"[Source: {source}, Page: {page_num} ({page_type})"
            if section:
                citation += f", Section: {section}"
            citation += "]"
            return citation
        else:
            # If not found, default to PDF page (most common)
            citation = f"[Source: {source}, Page: {page_num} (PDF page)"
            if section:
                citation += f", Section: {section}"
            citation += "]"
            return citation
    
    # Replace all citations in the answer
    fixed_answer = re.sub(citation_pattern, replace_citation, answer)
    return fixed_answer


# ============================================================================
# POST /api/chat Endpoint
# ============================================================================

@router.post("/", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    """
    Answer building code questions using RAG (Retrieval-Augmented Generation).
    
    This endpoint:
    1. Retrieves relevant context from building code PDFs using BM25-only retrieval (validated best)
    2. Passes context + user query to LLM
    3. Extracts citations from the response
    4. Returns answer with citations
    
    **How it works:**
    - Uses BM25-only retrieval (validated via RAGAS evaluation, composite score: 0.422)
    - BM25 catches exact terms (section numbers, citations, legal phrases)
    - Building codes benefit more from exact term matching than semantic similarity
    - LLM generates answer based on retrieved context
    - Citations extracted from metadata of retrieved documents
    
    Args:
        request: ChatRequest with user's question
    
    Returns:
        ChatResponse with answer and citations
    
    Raises:
        HTTPException: If vector store is not initialized or LLM fails
    
    Example request:
        {
            "query": "What is the minimum bedroom area required?"
        }
    
    Example response:
        {
            "answer": "According to the National Building Code, the minimum bedroom area is 9.5 square meters...",
            "citations": [
                {
                    "source": "National-Building-Code",
                    "page": 125,
                    "section": "5.2.3",
                    "text": "Minimum habitable room area shall be 9.5 m²..."
                }
            ]
        }
    """
    try:
        # Get vector store (initializes and indexes PDFs if needed)
        vector_store = get_vector_store()
        
        # Get BM25-only retriever (validated as best technique via RAGAS evaluation)
        # k=5 means retrieve top 5 documents
        # Default is BM25-only (composite score: 0.422, best among 4 techniques)
        retriever = vector_store.get_retriever(k=5)
        
        # Retrieve relevant context documents
        # Uses BM25-only retrieval: Exact term matching for section numbers, citations, legal phrases
        retrieved_docs = retriever.invoke(request.query)
        
        if not retrieved_docs:
            # No relevant documents found
            return ChatResponse(
                answer="I couldn't find relevant information in the building codes to answer your question. Please try rephrasing or asking about a different topic.",
                citations=[]
            )
        
        # Build context string from retrieved documents
        # Format: Combine all document contents with source metadata
        context_parts = []
        for i, doc in enumerate(retrieved_docs, 1):
            source = doc.metadata.get("source", "Unknown")
            
            # Prefer document page number if available, otherwise use PDF page
            page_document = doc.metadata.get("page_document")
            page_pdf = doc.metadata.get("page_pdf")
            
            if page_document:
                page = f"{page_document} (document page)"
            elif page_pdf:
                page = f"{page_pdf} (PDF page)"
            else:
                page = "?"
            
            section = doc.metadata.get("section", "")
            
            context_parts.append(
                f"[Document {i} - Source: {source}, Page: {page}"
                + (f", Section: {section}" if section else "")
                + "]\n"
                + doc.page_content
            )
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Create prompt template
        # This tells the LLM how to answer questions with citations
        from langchain_core.prompts import ChatPromptTemplate
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert building code assistant. Answer questions about building codes based on the provided context.

**Instructions:**
- Answer the question using ONLY information from the provided context
- If the context doesn't contain enough information, say so clearly
- Always cite your sources using the EXACT format from the context
- **CRITICAL**: When citing pages, you MUST include the page type indicator exactly as shown in the context:
  - If context shows "Page: 31 (PDF page)", cite as: [Source: Document Name, Page: 31 (PDF page), Section: Y.Y.Y]
  - If context shows "Page: 20 (document page)", cite as: [Source: Document Name, Page: 20 (document page), Section: Y.Y.Y]
- Example citations (copy the exact format):
  - [Source: National-Building-Code, Page: 31 (PDF page), Section: 5.2.3]
  - [Source: RA9514-RIRR-rev-2019-compressed, Page: 20 (document page), Section: 10.2.5.2]
  - [Source: Document-Name, Page: 99 (PDF page)]  (if no section)
- Be precise with numbers, units, and requirements
- If multiple sources have conflicting information, mention this
- Use SI units (meters, square meters, millimeters) as specified in the context

**Important:**
- Never make up building code requirements
- If you're uncertain, state that clearly
- This is informational only, not legal advice"""),
            ("human", """Answer this question about building codes:

Question: {query}

Context from building code documents:
{context}

Provide a clear, accurate answer with citations.

IMPORTANT: When citing pages, use the EXACT format from the context above, including "(PDF page)" or "(document page)" after the page number. For example:
- [Source: Document-Name, Page: 99 (PDF page), Section: 10.2.5.2]
- [Source: Document-Name, Page: 20 (document page), Section: 5.2.3]""")
        ])
        
        # Get LLM instance
        llm = get_llm(provider="openai", temperature=0.0)  # temperature=0 for deterministic answers
        
        # Create chain: prompt → LLM → response
        chain = prompt | llm
        
        # Invoke chain with query and context
        response = chain.invoke({
            "query": request.query,
            "context": context
        })
        
        # Extract answer text
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Post-process answer to fix citations (add page type indicators if missing)
        answer = _fix_citations_in_answer(answer, retrieved_docs)
        
        # Extract citations from retrieved documents
        # We use the metadata from the documents that were actually retrieved
        citations = []
        seen_sources = set()  # Avoid duplicate citations
        
        for doc in retrieved_docs:
            source = doc.metadata.get("source", "Unknown")
            
            # Prefer document page number if available, otherwise use PDF page
            page_document = doc.metadata.get("page_document")
            page_pdf = doc.metadata.get("page_pdf")
            
            # Format page with explicit type indication
            if page_document:
                page = f"{page_document} (document page)"
            elif page_pdf:
                page = f"{page_pdf} (PDF page)"
            else:
                page = None
            
            section = doc.metadata.get("section")
            
            # Create unique key for citation (avoid duplicates)
            # Use raw page numbers for uniqueness check
            citation_key = (source, page_document or page_pdf, section)
            if citation_key not in seen_sources:
                citations.append(Citation(
                    source=source,
                    page=page,
                    section=section,
                    text=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                ))
                seen_sources.add(citation_key)
        
        # Return response with answer and citations
        return ChatResponse(
            answer=answer,
            citations=citations
        )
        
    except ValueError as e:
        # Handle validation errors (e.g., missing API key)
        raise HTTPException(
            status_code=400,
            detail=f"Configuration error: {str(e)}"
        )
    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Error processing chat request: {str(e)}"
        )