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
from typing import List, Optional, Dict
from pathlib import Path
import os
import uuid

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.core.llm import get_llm, setup_llm_cache
from app.services.vector_store import VectorStore
from app.services.pdf_ingest import ingest_pdf
from app.models.domain import Room


# ============================================================================
# Pydantic Models for Request/Response
# ============================================================================

class ChatRequest(BaseModel):
    """
    Request model for chat endpoint.
    
    Fields:
    - query: User's question about building codes
    - conversation_id: Optional conversation ID for maintaining context across messages
    - blueprint_context: Optional list of rooms from uploaded blueprint for context-aware responses
    """
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="User's question about building codes"
    )
    conversation_id: Optional[str] = Field(
        None,
        description="Conversation ID for maintaining context across messages"
    )
    blueprint_context: Optional[List[Room]] = Field(
        None,
        description="List of rooms from uploaded blueprint for context-aware responses"
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
    - conversation_id: Conversation ID (always returned, even if newly generated)
    """
    answer: str = Field(..., description="LLM-generated answer to the question")
    citations: List[Citation] = Field(
        default_factory=list,
        description="List of source citations"
    )
    conversation_id: str = Field(..., description="Conversation ID for maintaining context across messages")


# ============================================================================
# API Router Setup
# ============================================================================

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"]  # Groups endpoints in API docs
)


# ============================================================================
# Conversation Storage (In-Memory)
# ============================================================================

# Global conversation storage (in-memory for MVP)
# Format: {conversation_id: [{"role": "human"|"ai", "content": "..."}, ...]}
_conversations: Dict[str, List[Dict[str, str]]] = {}


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

def _generate_conversation_id() -> str:
    """
    Generate a unique conversation ID.
    
    Uses UUID4 to generate a unique identifier for each conversation.
    
    Returns:
        A unique conversation ID string (e.g., "conv_550e8400-e29b-41d4-a716-446655440000")
    """
    return f"conv_{uuid.uuid4().hex}"


def _get_conversation_history(conversation_id: str) -> List[Dict[str, str]]:
    """
    Retrieve conversation history for a given conversation ID.
    
    Args:
        conversation_id: The unique identifier for the conversation
    
    Returns:
        List of message dictionaries with "role" and "content" keys.
        Returns empty list if conversation doesn't exist.
    """
    return _conversations.get(conversation_id, [])


def _save_message(conversation_id: str, role: str, content: str) -> None:
    """
    Save a message to the conversation history.
    
    Args:
        conversation_id: The unique identifier for the conversation
        role: Message role, either "human" or "ai"
        content: The message content
    
    Note:
        Creates a new conversation entry if the conversation_id doesn't exist.
    """
    if conversation_id not in _conversations:
        _conversations[conversation_id] = []
    
    _conversations[conversation_id].append({
        "role": role,
        "content": content
    })


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
    Answer building code questions using RAG (Retrieval-Augmented Generation)
    with conversational context and blueprint integration.
    
    **NEW FEATURES:**
    - Maintains conversation history across messages
    - Integrates extracted blueprint room data into context
    - Enables follow-up questions and context-aware responses
    
    **How it works:**
    1. Handles conversation_id (generates new or uses existing)
    2. Retrieves conversation history if conversation_id exists
    3. Builds blueprint context string from extracted rooms (if provided)
    4. Retrieves relevant documents using BM25-only retrieval
    5. Constructs prompt with conversation history + blueprint context + current query
    6. Calls LLM with full context
    7. Stores new messages in conversation history
    8. Returns response with conversation_id
    
    Args:
        request: ChatRequest with:
            - query: User's question
            - conversation_id: Optional conversation ID (generated if not provided)
            - blueprint_context: Optional list of extracted Room objects
    
    Returns:
        ChatResponse with answer, citations, and conversation_id
    """
    try:
        # ========================================================================
        # STEP 1: Handle Conversation ID
        # ========================================================================
        # If no conversation_id provided, generate a new one
        # If provided, we'll use it to retrieve conversation history
        conversation_id = request.conversation_id
        
        if not conversation_id:
            # Generate new conversation ID using UUID
            # This creates a unique identifier for this conversation session
            conversation_id = _generate_conversation_id()
            print(f"Generated new conversation_id: {conversation_id}")
        else:
            print(f"Using existing conversation_id: {conversation_id}")
        
        # ========================================================================
        # STEP 2: Retrieve Conversation History
        # ========================================================================
        # Get previous messages from this conversation (if any)
        # This allows the LLM to understand context from earlier messages
        conversation_history = _get_conversation_history(conversation_id)
        
        # Convert stored messages to LangChain message format
        # LangChain expects tuples: ("human", content) or ("ai", content)
        langchain_history = []
        for msg in conversation_history:
            if msg["role"] == "human":
                langchain_history.append(("human", msg["content"]))
            elif msg["role"] == "ai":
                langchain_history.append(("ai", msg["content"]))
        
        print(f"Retrieved {len(langchain_history)} previous messages from conversation")
        
        # ========================================================================
        # STEP 3: Build Blueprint Context String (if provided)
        # ========================================================================
        # If user has uploaded a blueprint and extracted rooms, include them in context
        # This allows the LLM to reference specific rooms when answering questions
        blueprint_context_str = ""
        if request.blueprint_context and len(request.blueprint_context) > 0:
            # Build a formatted string listing all extracted rooms
            blueprint_context_str = "\n\n**User's Blueprint Context:**\n"
            blueprint_context_str += "The user has uploaded a blueprint with the following rooms:\n"
            
            for room in request.blueprint_context:
                # Format: Room Name (Type): Area m²
                # Example: "Bedroom 1 (bedroom): 14.5 m²"
                blueprint_context_str += f"- {room.name} ({room.type}): {room.area_m2} m²\n"
            
            blueprint_context_str += "\nYou can reference these specific rooms when answering questions. "
            blueprint_context_str += "For example, if asked 'Is bedroom 1 compliant?', you can check the area "
            blueprint_context_str += "against building code requirements.\n"
            
            print(f"Including blueprint context with {len(request.blueprint_context)} rooms")
        
        # ========================================================================
        # STEP 4: Retrieve Relevant Documents (RAG)
        # ========================================================================
        # This part remains the same - we still use RAG to find relevant building code sections
        vector_store = get_vector_store()
        retriever = vector_store.get_retriever(k=5)  # Get top 5 documents
        
        # Retrieve documents based on the current query
        # Note: We could also consider previous queries for better retrieval, but for MVP
        # we'll use just the current query
        retrieved_docs = retriever.invoke(request.query)
        
        if not retrieved_docs:
            # No relevant documents found - still return a response but with conversation_id
            # Store the user's question and our response in conversation history
            _save_message(conversation_id, "human", request.query)
            _save_message(conversation_id, "ai", 
                "I couldn't find relevant information in the building codes to answer your question. "
                "Please try rephrasing or asking about a different topic.")
            
            return ChatResponse(
                answer="I couldn't find relevant information in the building codes to answer your question. Please try rephrasing or asking about a different topic.",
                citations=[],
                conversation_id=conversation_id  # NEW: Return conversation_id
            )
        
        # ========================================================================
        # STEP 5: Build Document Context String
        # ========================================================================
        # Format retrieved documents into a readable context string
        # This is the same as before
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
        
        # ========================================================================
        # STEP 6: Build System Prompt with Blueprint Context
        # ========================================================================
        # Update the system prompt to mention blueprint context if available
        system_prompt = """You are an expert building code assistant. Answer questions about building codes based on the provided context.

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
- Use SI units (meters, square meters, millimeters) as specified in the context"""
        
        # Add blueprint context instructions if blueprint is provided
        if blueprint_context_str:
            system_prompt += "\n\n**Blueprint Context:**\n"
            system_prompt += "The user has uploaded a blueprint. You can reference specific rooms from their blueprint "
            system_prompt += "when answering questions. Use the room names and areas provided in the blueprint context."
        
        system_prompt += """

**Important:**
- Never make up building code requirements
- If you're uncertain, state that clearly
- This is informational only, not legal advice"""
        
        # ========================================================================
        # STEP 7: Build Human Message with Full Context
        # ========================================================================
        # Construct the human message that includes:
        # 1. The current query
        # 2. Blueprint context (if available)
        # 3. Document context from RAG
        human_message_template = """Answer this question about building codes:

Question: {query}
"""
        
        # Add blueprint context to human message if available
        if blueprint_context_str:
            human_message_template += blueprint_context_str
        
        human_message_template += """
Context from building code documents:
{context}

Provide a clear, accurate answer with citations.

IMPORTANT: When citing pages, use the EXACT format from the context above, including "(PDF page)" or "(document page)" after the page number. For example:
- [Source: Document-Name, Page: 99 (PDF page), Section: 10.2.5.2]
- [Source: Document-Name, Page: 20 (document page), Section: 5.2.3]"""
        
        # ========================================================================
        # STEP 8: Create Prompt Template with Conversation History
        # ========================================================================
        # Build the complete message list for LangChain:
        # 1. System prompt (instructions)
        # 2. Conversation history (previous messages)
        # 3. Current human message (query + context)
        from langchain_core.prompts import ChatPromptTemplate
        
        # Start with system message
        messages = [("system", system_prompt)]
        
        # Add conversation history (previous messages in this conversation)
        # This is what makes it conversational - the LLM can see what was said before
        messages.extend(langchain_history)
        
        # Add current human message
        messages.append(("human", human_message_template))
        
        # Create the prompt template
        prompt = ChatPromptTemplate.from_messages(messages)
        
        # ========================================================================
        # STEP 9: Call LLM with Full Context
        # ========================================================================
        # Get LLM instance (same as before)
        llm = get_llm(provider="openai", temperature=0.0)  # temperature=0 for deterministic answers
        
        # Create chain: prompt → LLM → response
        chain = prompt | llm
        
        # Invoke chain with all context variables
        # The prompt template will substitute {query} and {context} with actual values
        response = chain.invoke({
            "query": request.query,
            "context": context
        })
        
        # Extract answer text from LLM response
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Post-process answer to fix citations (add page type indicators if missing)
        answer = _fix_citations_in_answer(answer, retrieved_docs)
        
        # ========================================================================
        # STEP 10: Store Messages in Conversation History
        # ========================================================================
        # Save the user's question to conversation history
        _save_message(conversation_id, "human", request.query)
        
        # Save the AI's response to conversation history
        _save_message(conversation_id, "ai", answer)
        
        print(f"Stored new messages in conversation {conversation_id}")
        
        # ========================================================================
        # STEP 11: Extract Citations (same as before)
        # ========================================================================
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
            citation_key = (source, page_document or page_pdf, section)
            if citation_key not in seen_sources:
                citations.append(Citation(
                    source=source,
                    page=page,
                    section=section,
                    text=doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                ))
                seen_sources.add(citation_key)
        
        # ========================================================================
        # STEP 12: Return Response with Conversation ID
        # ========================================================================
        # Return the response, now including conversation_id so frontend can maintain it
        return ChatResponse(
            answer=answer,
            citations=citations,
            conversation_id=conversation_id  # NEW: Always return conversation_id
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