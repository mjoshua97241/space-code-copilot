"""
Rule extraction service: Extract structured rules from building code PDFs using LLM.

MVP core feature - extracts rules from PDFs for compliance checking.
"""
import os
from typing import List
from pathlib import Path
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.runnables import RunnablePassthrough

from app.core.llm import get_llm
from app.models.domain import Rule, ProjectContext
from app.services.vector_store import VectorStore

# Load environment variables
env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

def extract_rules_from_pdf(
    pdf_path: str | Path,
    vector_store: VectorStore,
    project_context: ProjectContext,
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
    
    # Build project context summary for prompt
    context_summary = f"""
PROJECT CONTEXT:
- Building type: {project_context.building_type}
- Number of stories: {project_context.number_of_stories}
- Occupancy: {project_context.occupancy}
- Building classification: {project_context.building_classification}
- Requires accessibility: {project_context.requires_accessibility}
- Requires fire-rated: {project_context.requires_fire_rated}
"""
    
    # Build exclusion list based on context
    exclusions = []
    if project_context.building_type == "residential":
        exclusions.append("- Commercial, industrial, or public building rules")
        exclusions.append("- Rules for multi-tenant or commercial occupancy")
    if project_context.number_of_stories == "single-story":
        exclusions.append("- Fire exit doors and stairwell requirements")
        exclusions.append("- Emergency exit requirements for multi-story buildings")
        exclusions.append("- Rules specific to multi-story buildings")
    if not project_context.requires_accessibility:
        exclusions.append("- Public accessibility requirements (ADA, universal design)")
        exclusions.append("- Accessible door widths (unless standard residential doors)")
    if not project_context.requires_fire_rated:
        exclusions.append("- Fire-rated door requirements")
        exclusions.append("- Fire exit requirements")
    
    exclusion_text = "\n".join(exclusions) if exclusions else "- None (all rules applicable)"
    
    # Prompt for rule extraction
    extraction_prompt = ChatPromptTemplate.from_messages([
        ("system", """You are an expert at extracting building code rules from documents.

{project_context}

EXTRACTION RULES:
- Only extract rules that apply to THIS specific project context
- EXCLUDE the following (they do NOT apply to this project):
{exclusions}

Focus on:
- Minimum area requirements for {building_type} rooms
- Minimum width requirements for {building_type} doors
- Rules applicable to {occupancy} {building_classification} buildings
- Rules for {number_of_stories} buildings

IMPORTANT CONSTRAINTS:
- element_type MUST be exactly "room" or "door" (no other values allowed)
- rule_type MUST be "area_min", "width_min", or "text"
- For room area rules: element_type="room", rule_type="area_min"
- For door width rules: element_type="door", rule_type="width_min"
- Only extract rules that apply to rooms or doors

For each rule, extract:
- Rule name (clear, descriptive)
- Rule type (area_min, width_min, or text)
- Element type (MUST be "room" or "door" only)
- Minimum value (if numeric)
- Code reference (section number, if available)

Return only rules that have clear, measurable requirements. Use SI units (m² for area, mm for width)."""),
        ("human", """Extract building code rules from this context:

{context}

{project_context}

Extract up to {max_rules} rules. Return as a JSON array of Rule objects with these fields:
- id: Unique identifier (e.g., "R003", "D003")
- name: Clear descriptive name
- rule_type: "area_min", "width_min", or "text"
- element_type: MUST be "room" or "door" (no other values)
- min_value: Numeric value if applicable (null otherwise)
- code_ref: Building code reference (section number, if available)
- rule_text: Text description (optional)

Format as JSON array. Only include rules for rooms or doors that match the project context.""")
    ])
    
    # LLM with structured output
    llm = get_llm(provider="openai", temperature=0.0)
    
    # Create chain: retrieve context → format → LLM → parse
    def format_docs(docs):
        formatted = []
        for doc in docs:
            source = doc.metadata.get('source', 'Unknown')
            
            # Prefer document page number if available, otherwise use PDF page
            page_document = doc.metadata.get('page_document')
            page_pdf = doc.metadata.get('page_pdf')
            
            # Format page with explicit type indication
            if page_document:
                page = f"{page_document} (document page)"
            elif page_pdf:
                page = f"{page_pdf} (PDF page)"
            else:
                page = '?'
            
            formatted.append(f"[Source: {source}, Page: {page}]\n{doc.page_content}")
        return "\n\n---\n\n".join(formatted)
    
    # Extract rules (using a general query to find all rule-like sections)
    query = "minimum area requirements room dimensions door width accessibility"
    
    try:
        # Retrieve documents
        retrieved_docs = retriever.invoke(query)
        
        # Format context
        context = format_docs(retrieved_docs)
        
        # Invoke LLM with prompt
        response = extraction_prompt.invoke({
            "context": context,
            "max_rules": max_rules,
            "project_context": context_summary,
            "building_type": project_context.building_type,
            "number_of_stories": project_context.number_of_stories,
            "occupancy": project_context.occupancy,
            "building_classification": project_context.building_classification,
            "exclusions": exclusion_text
        })
        response = llm.invoke(response)
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
                # Validate and filter element_type (must be "room" or "door")
                element_type = rule_data.get("element_type", "room")
                if element_type not in ["room", "door"]:
                    # Skip invalid element types
                    print(f"  Skipping rule with invalid element_type: {element_type}")
                    continue
                
                # Validate rule_type matches element_type
                rule_type = rule_data.get("rule_type", "text")
                if element_type == "room" and rule_type not in ["area_min", "text"]:
                    # Room rules should be area_min or text, not width_min
                    print(f"  Fixing rule_type for room rule: {rule_type} -> text")
                    rule_type = "text"
                elif element_type == "door" and rule_type not in ["width_min", "text"]:
                    # Door rules should be width_min or text, not area_min
                    if rule_type == "area_min":
                        print(f"  Fixing rule_type for door rule: {rule_type} -> text")
                        rule_type = "text"
                
                # Ensure all required fields are present
                try:
                    rule = Rule(
                        id=rule_data.get("id", f"EXTRACTED_{len(rules) + 1}"),
                        name=rule_data.get("name", "Extracted rule"),
                        rule_type=rule_type,
                        element_type=element_type,
                        min_value=rule_data.get("min_value"),
                        code_ref=rule_data.get("code_ref"),
                        rule_text=rule_data.get("rule_text")
                    )
                    rules.append(rule)
                except Exception as e:
                    # Skip invalid rules
                    print(f"  Skipping invalid rule: {e}")
                    continue
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
    project_context: ProjectContext,
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
    rule_counter = {"R": 100, "D": 100}  # Start extracted IDs at 100 to avoid conflicts with seeded (R001-D002)
    
    for pdf_path in pdf_paths:
        pdf_path_obj = Path(pdf_path)
        if not pdf_path_obj.exists():
            print(f"Warning: PDF not found: {pdf_path}")
            continue
        
        print(f"Extracting rules from {pdf_path_obj.name}...")
        extracted = extract_rules_from_pdf(
            pdf_path_obj,
            vector_store,
            project_context,
            max_rules=max_rules_per_pdf
        )
        
        # Filter duplicates and assign unique IDs
        for rule in extracted:
            # Generate unique ID if it conflicts with existing or seeded rules
            original_id = rule.id
            if original_id in seen_rule_ids or original_id in ["R001", "R002", "D001", "D002"]:
                # Generate new ID based on element type
                prefix = "R" if rule.element_type == "room" else "D"
                new_id = f"{prefix}{rule_counter[prefix]:03d}"
                rule_counter[prefix] += 1
                rule.id = new_id
                print(f"  Renamed rule ID from {original_id} to {new_id} (conflict)")
            
            if rule.id not in seen_rule_ids:
                all_rules.append(rule)
                seen_rule_ids.add(rule.id)
        
        print(f"  Extracted {len(extracted)} rules from {pdf_path_obj.name}")
    
    print(f"Total extracted rules: {len(all_rules)}")
    return all_rules