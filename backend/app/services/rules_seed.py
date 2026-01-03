from typing import List

from app.models.domain import Rule, ProjectContext

# ============================================================================
# Seeded Building Code Rules
# ============================================================================

def get_seeded_rules() -> List[Rule]:
    """
    Return hardcoded building code rules for MVP.

    These are simple numeric rules to get compliance checking working.

    **LLM Integration:**
    - These rules work alongside LLM-extracted rules from PDFs
    - Use `get_all_rules()` to combine seeded + extracted rules
    - LLM extraction is the MVP core feature (rule_extractor.py)
    """
    return [
        # ==============================================================
        # Room Area Rules
        # ==============================================================

        Rule(
            id="R001",
            name="Minimum bedroom area",
            rule_type="area_min",
            element_type="room",
            min_value=9.5, # m²
            code_ref="NBC Section 8.2.1 - Minimum habitable room area"
        ),

        Rule(
            id="R002",
            name="Minimum living room area",
            rule_type="area_min",
            element_type="room",
            min_value=12.0, # m²
            code_ref="NBC Section 8.2.2 - Minimum living area"
        ),

        # ==============================================================
        # Door Width Rules
        # ==============================================================

        Rule(
            id="D001",
            name="Minimum accessible door width",
            rule_type="width_min",
            element_type="door",
            min_value=800.0, # mm (0.8 meters)
            code_ref="NBC Section 8.3.2 - Accessible door clear width"            
        ),

        Rule(
            id="D002",
            name="Minimum standard door width",
            rule_type="width_min",
            element_type="door",
            min_value=700.0, # mm (0.7 meters)
            code_ref="NBC Section 8.3.1 - Standard door clear width"
        ),
    ]

def get_default_project_context() -> ProjectContext:
    """
    Get default project context for single-floor residential detached house.
    
    This matches the current MVP project. Can be customized per project.
    
    Returns:
        ProjectContext with default values for residential single-story detached house
    """
    return ProjectContext(
        building_type="residential",
        number_of_stories="single-story",
        occupancy="single-family",
        building_classification="detached",
        requires_accessibility=False,
        requires_fire_rated=False
    )


def get_all_rules(project_context: ProjectContext | None = None) -> List[Rule]:
    """
    Combine seeded rules with LLM-extracted rules from PDFs.

    This is the main function the compliance checker will use.
    It combines:
    - Seeded rules (hardcoded, deterministic)
    - LLM-extracted rules (from PDFs via rule_extractor.py)

    **LLM Integration:**
    Extracts rules from PDFs in app/data/ directory.
    Uses project context to filter rules to only those applicable.
    Falls back to seeded rules only if extraction fails.

    Args:
        project_context: Project context for filtering rules. If None, uses default
                         (single-floor residential detached house).

    Returns:
        Combined list of all rules (seeded + extracted)
    """
    from pathlib import Path
    from app.services.rule_extractor import extract_rules_from_pdfs
    
    # Use default context if not provided
    if project_context is None:
        project_context = get_default_project_context()
    
    seeded = get_seeded_rules()
    
    # Find PDFs in app/data/ directory
    data_dir = Path(__file__).parent.parent / "data"
    pdf_paths = list(data_dir.glob("*.pdf"))
    
    if not pdf_paths:
        print("No PDFs found in app/data/, using seeded rules only")
        return seeded
    
    try:
        # Extract rules from PDFs
        # Use singleton vector store pattern (shared with chat endpoint)
        from app.services.vector_store import VectorStore
        vector_store = VectorStore()
        
        print(f"Extracting rules with project context: {project_context.building_type} {project_context.number_of_stories} {project_context.occupancy} {project_context.building_classification}")
        
        extracted = extract_rules_from_pdfs(
            pdf_paths,
            project_context=project_context,
            vector_store=vector_store,
            max_rules_per_pdf=15
        )
        
        # Combine seeded + extracted
        all_rules = seeded + extracted
        
        print(f"Total rules: {len(seeded)} seeded + {len(extracted)} extracted = {len(all_rules)} total")
        return all_rules
        
    except Exception as e:
        # Fallback to seeded rules if extraction fails
        print(f"Error extracting rules from PDFs: {e}")
        print("Falling back to seeded rules only")
        return seeded

# ==============================================================
# Rule Filtering Helpers
# ==============================================================

def get_rules_for_element_type(element_type: str) -> List[Rule]:
    """
    Get all rules that apply to a specific element type.

    Useful for compliance checker to filter rules before checking.

    Args:
        element_type: "room" or "door"
    
    Returns:
        Filtered list of rules for that element type.
    
    Example:
        room_rules = get_rules_for_element_type("room")
        # Returns only rules with element_type="room"
    """
    all_rules = get_all_rules()  # Changed from get_seeded_rules()
    return [rule for rule in all_rules if rule.element_type == element_type]

def get_rules_by_type(rule_type: str) -> List[Rule]:
    """
    Get all rules of a specific type (area_min, width_min, text).

    Useful for understanding what types of checks are available.

    Args:
        rule_type: "area_min", "width_min", or "text"

    Returns:
        Filtered list of rules of that type.
    
    Example:
        area_rules = get_rules_by_type("area_min")
        # Returns only area_min rules
    """
    all_rules = get_all_rules()  # Changed from get_seeded_rules()
    return [rule for rule in all_rules if rule.rule_type == rule_type]

def get_rule_by_id(rule_id: str) -> Rule | None:
    """
    Get a specific rule by its ID.

    Useful for looking up rule details when creating Issue objects.

    Args:
        rule_id: Rule identifier (e.g., "R001", "D001", "EXTRACTED_1")
    
    Returns:
        Rule object if found, None otherwise.
    
    Example:
        rule = get_rule_by_id("R001")
        # Returns Rule(id="R001", name="Minimum bedroom area", ...)
    """
    all_rules = get_all_rules()  # Changed from get_seeded_rules()
    for rule in all_rules:
        if rule.id == rule_id:
            return rule
    return None