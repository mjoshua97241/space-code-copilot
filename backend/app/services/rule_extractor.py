"""
Rule extraction service: Extract structured rules from building code PDFs using LLM.

MVP core feature - extracts rules from PDFs for compliance checking.
"""
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.llm import get_llm
from app.models.domain import Rule
from app.services.vector_store import VectorStore


def extract_rules_from_pdf(
    pdf_path: str,
    vector_store: VectorStore,
    max_rules: int = 20
) -> List[Rule]:
    """
    Extract structured rules from building code PDF using LLM.
    
    Process:
    1. Load PDF and add to vector store (if not already added)
    2. Use RAG to find relevant code sections
    3. Use LLM with structured output to extract Rule objects
    
    Args:
        pdf_path: Path to building code PDF
        vector_store: VectorStore instance with PDF indexed
        max_rules: Maximum number of rules to extract
    
    Returns:
        List of Rule objects extracted from PDF
    """
    from app.services.pdf_ingest import ingest_pdf
    
    # Load and index PDF if needed
    # TODO: Check if already indexed (future optimization)
    chunks = ingest_pdf(pdf_path)
    vector_store.add_documents(chunks)
    
    # Get retriever
    retriever = vector_store.get_retriever(k=10)
    
    # Prompt for rule extraction
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting building code rules from documents.
        
Extract structured rules from the provided building code context. Focus on:
- Minimum area requirements for rooms
- Minimum width requirements for doors/corridors
- Accessibility requirements
- Any numeric constraints (dimensions, areas)

For each rule, extract:
- Rule name (clear, descriptive)
- Rule type (area_min, width_min, or text)
- Element type (room, door, or corridor)
- Minimum value (if numeric)
- Rule text (exact quote or summary)
- Code reference (section number, if available)

Return only rules that have clear, measurable requirements."""),
        ("human", """Extract building code rules from this context:

{context}

Extract up to {max_rules} rules. Return as structured Rule objects.""")
    ])
    
    # LLM with structured output
    llm = get_llm(provider="openai", temperature=0.0)
    
    # Pydantic output parser
    parser = PydanticOutputParser(pydantic_object=Rule)
    
    # Chain: retrieve context → extract rules
    chain = (
        {
            "context": retriever,
            "max_rules": RunnablePassthrough()
        }
        | extraction_prompt
        | llm
        | parser
    )
    
    # Extract rules (using a general query to find all rule-like sections)
    query = "minimum area requirements room dimensions door width accessibility"
    result = chain.invoke({"question": query, "max_rules": max_rules})
    
    # Handle single rule vs list
    if isinstance(result, Rule):
        return [result]
    elif isinstance(result, list):
        return result
    else:
        return []