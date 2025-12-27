from typing import List

from app.models.domain import Room, Door, Rule, Issue
from app.services.rules_seed import get_all_rules


# ============================================================================
# Room Compliance Checking
# ============================================================================

def check_room_compliance(room: Room, rules: List[Rule]) -> List[Issue]:
    """
    Check a single room against applicable rules.
    
    Applies all rules that:
    - Have element_type="room"
    - Have rule_type="area_min" (for now - future: handle "text" rules with LLM)
    
    Args:
        room: Room object to check
        rules: List of all rules (will be filtered to room rules)
    
    Returns:
        List of Issue objects for any violations found.
    
    Example:
        issues = check_room_compliance(room, all_rules)
        # Returns [] if compliant, [Issue(...)] if violations found
    """
    issues = []
    
    # Filter to only room rules
    room_rules = [rule for rule in rules if rule.element_type == "room"]
    
    for rule in room_rules:
        # Only check numeric rules for now (area_min, width_min)
        # Future: "text" rules will require LLM interpretation
        if rule.rule_type == "area_min":
            if rule.min_value is not None:
                if room.area_m2 < rule.min_value:
                    # Create violation issue
                    issue = Issue(
                        element_id=room.id,
                        element_type="room",
                        rule_id=rule.id,
                        message=(
                            f"Room '{room.name}' ({room.id}) has area {room.area_m2:.2f} m², "
                            f"but minimum required is {rule.min_value:.2f} m² "
                            f"({rule.name})"
                        ),
                        code_ref=rule.code_ref,
                        severity="error"
                    )
                    issues.append(issue)
    
    return issues


# ============================================================================
# Door Compliance Checking
# ============================================================================

def check_door_compliance(door: Door, rules: List[Rule]) -> List[Issue]:
    """
    Check a single door against applicable rules.
    
    Applies all rules that:
    - Have element_type="door"
    - Have rule_type="width_min" (for now - future: handle "text" rules with LLM)
    
    Args:
        door: Door object to check
        rules: List of all rules (will be filtered to door rules)
    
    Returns:
        List of Issue objects for any violations found.
    
    Example:
        issues = check_door_compliance(door, all_rules)
        # Returns [] if compliant, [Issue(...)] if violations found
    """
    issues = []
    
    # Filter to only door rules
    door_rules = [rule for rule in rules if rule.element_type == "door"]
    
    for rule in door_rules:
        if rule.rule_type == "width_min":
            if rule.min_value is not None:
                if door.clear_width_mm < rule.min_value:
                    # Create violation issue
                    issue = Issue(
                        element_id=door.id,
                        element_type="door",
                        rule_id=rule.id,
                        message=(
                            f"Door '{door.id}' has clear width {door.clear_width_mm:.0f} mm, "
                            f"but minimum required is {rule.min_value:.0f} mm "
                            f"({rule.name})"
                        ),
                        code_ref=rule.code_ref,
                        severity="error"
                    )
                    issues.append(issue)
    
    return issues


# ============================================================================
# Main Compliance Checker
# ============================================================================

def check_compliance(
    rooms: List[Room],
    doors: List[Door],
    rules: List[Rule] | None = None
) -> List[Issue]:
    """
    Check all rooms and doors against building code rules.
    
    This is the main function that orchestrates compliance checking.
    It:
    1. Loads rules (if not provided)
    2. Checks each room against room rules
    3. Checks each door against door rules
    4. Returns all violations as Issue objects
    
    Args:
        rooms: List of Room objects to check
        doors: List of Door objects to check
        rules: Optional list of rules. If None, uses get_all_rules()
    
    Returns:
        List of Issue objects representing all violations found.
    
    Example:
        from app.services.design_loader import load_design
        
        rooms, doors = load_design()
        issues = check_compliance(rooms, doors)
        
        if issues:
            print(f"Found {len(issues)} compliance issues")
            for issue in issues:
                print(f"- {issue.message}")
        else:
            print("Design is compliant!")
    """
    # Load rules if not provided
    if rules is None:
        rules = get_all_rules()
    
    all_issues = []
    
    # Check all rooms
    for room in rooms:
        room_issues = check_room_compliance(room, rules)
        all_issues.extend(room_issues)
    
    # Check all doors
    for door in doors:
        door_issues = check_door_compliance(door, rules)
        all_issues.extend(door_issues)
    
    return all_issues


# ============================================================================
# Helper Functions
# ============================================================================

def check_room_by_type(room: Room, rules: List[Rule]) -> List[Issue]:
    """
    Check room with type-specific rule filtering.
    
    Future enhancement: Filter rules by room.type (e.g., bedroom rules
    only apply to bedrooms). For now, applies all room rules.
    
    Args:
        room: Room object to check
        rules: List of all rules
    
    Returns:
        List of Issue objects for violations.
    """
    # For MVP: apply all room rules
    # Future: filter by room.type matching rule conditions
    return check_room_compliance(room, rules)


def get_compliance_summary(issues: List[Issue]) -> dict:
    """
    Get a summary of compliance issues.
    
    Useful for reporting and UI display.
    
    Args:
        issues: List of Issue objects
    
    Returns:
        Dictionary with summary statistics.
    
    Example:
        summary = get_compliance_summary(issues)
        # Returns: {
        #   "total": 2,
        #   "by_element_type": {"room": 0, "door": 2},
        #   "by_severity": {"error": 2, "warning": 0}
        # }
    """
    summary = {
        "total": len(issues),
        "by_element_type": {
            "room": len([i for i in issues if i.element_type == "room"]),
            "door": len([i for i in issues if i.element_type == "door"])
        },
        "by_severity": {
            "error": len([i for i in issues if i.severity == "error"]),
            "warning": len([i for i in issues if i.severity == "warning"])
        }
    }
    return summary