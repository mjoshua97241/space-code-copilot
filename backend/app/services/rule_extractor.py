"""
Rule extraction service: Extract structured rules from building code PDFs using LLM.

MVP core feature - extracts rules from PDFs for compliance checking.
"""
from typing import List
from pathlib import Path
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.llm import get_llm
from app.models.domain import Rule
from app.services.vector_store import VectorStore


def extract_rules_from_pdf(
    pdf_path: str | Path,
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
    
    # Get retriever (uses BM25-only by default, validated best)
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

Return only rules that have clear, measurable requirements. Use SI units (m² for area, mm for width)."""),
        ("human", """Extract building code rules from this context:

{context}

Extract up to {max_rules} rules. Return as a JSON array of Rule objects with these fields:
- id: Unique identifier (e.g., "R003", "D003")
- name: Clear descriptive name
- rule_type: "area_min", "width_min", or "text"
- element_type: "room", "door", or "corridor"
- min_value: Numeric value if applicable (null otherwise)
- code_ref: Building code reference (section number, if available)
- rule_text: Text description (optional)

Format as JSON array.""")
    ])
    
    # LLM with structured output
    llm = get_llm(provider="openai", temperature=0.0)
    
    # Create chain: retrieve context → format → LLM → parse
    def format_docs(docs):
        return "\n\n---\n\n".join([
            f"[Source: {doc.metadata.get('source', 'Unknown')}, Page: {doc.metadata.get('page', '?')}]\n{doc.page_content}"
            for doc in docs
        ])
    
    # Chain: query → retrieve → format → prompt → LLM
    chain = (
        {
            "context": retriever | format_docs,
            "max_rules": RunnablePassthrough()
        }
        | extraction_prompt
        | llm
    )
    
    # Extract rules (using a general query to find all rule-like sections)
    query = "minimum area requirements room dimensions door width accessibility"
    
    try:
        response = chain.invoke({"query": query, "max_rules": max_rules})
        answer = response.content if hasattr(response, 'content') else str(response)
        
        # Parse JSON response manually (LLM returns JSON string)
        import json
        import re
        
        # Extract JSON array from response
        json_match = re.search(r'\[.*\]', answer, re.DOTALL)
        if json_match:
            rules_data = json.loads(json_match.group())
            rules = []
            for rule_data in rules_data:
                # Ensure all required fields are present
                rule = Rule(
                    id=rule_data.get("id", f"EXTRACTED_{len(rules) + 1}"),
                    name=rule_data.get("name", "Extracted rule"),
                    rule_type=rule_data.get("rule_type", "text"),
                    element_type=rule_data.get("element_type", "room"),
                    min_value=rule_data.get("min_value"),
                    code_ref=rule_data.get("code_ref"),
                    rule_text=rule_data.get("rule_text")
                )
                rules.append(rule)
            return rules
        else:
            # Fallback: try to parse as single rule
            rule_match = re.search(r'\{.*\}', answer, re.DOTALL)
            if rule_match:
                rule_data = json.loads(rule_match.group())
                return [Rule(**rule_data)]
            return []
    except Exception as e:
        # Log error but don't fail - return empty list
        print(f"Error extracting rules from {pdf_path}: {e}")
        return []


def extract_rules_from_pdfs(
    pdf_paths: List[str | Path],
    vector_store: VectorStore | None = None,
    max_rules_per_pdf: int = 15
) -> List[Rule]:
    """
    Extract rules from multiple PDF files.
    
    This is the main function to call from rules_seed.py.
    
    Args:
        pdf_paths: List of paths to building code PDFs
        vector_store: Optional VectorStore instance. If None, creates a new one.
        max_rules_per_pdf: Maximum rules to extract per PDF
    
    Returns:
        Combined list of all extracted rules from all PDFs
    """
    from app.services.vector_store import VectorStore as VS
    
    # Use provided vector store or create new one
    if vector_store is None:
        vector_store = VS()
    
    all_rules = []
    seen_rule_ids = set()  # Avoid duplicates
    
    for pdf_path in pdf_paths:
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            print(f"Warning: PDF not found: {pdf_path}")
            continue
        
        print(f"Extracting rules from {pdf_path_obj.name}...")
        extracted = extract_rules_from_pdf(
            pdf_path_obj,
            vector_store,
            max_rules=max_rules_per_pdf
        )
        
        # Filter duplicates and add unique rules
        for rule in extracted:
            if rule.id not in seen_rule_ids:
                all_rules.append(rule)
                seen_rule_ids.add(rule.id)
        
        print(f"  Extracted {len(extracted)} rules from {pdf_path_obj.name}")
    
    print(f"Total extracted rules: {len(all_rules)}")
    return all_rules