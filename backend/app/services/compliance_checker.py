from typing import List

from app.models.domain import Rule, Room, Issue, Door

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
                # Create violation issue
                issue = Issue(
                    element_id=room.id,
                    element_type="room",
                    rule_id=rule.id,
                    message=(
                        f"""
                        Room '{room.name}' ({room.id}) has area {room.area_m2:.2f} m²,
                        but minimum required is {rule.min_value:.2f} m²
                        ({rule.name})
                        """
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
            if rule.clear_width_mm is not None:
                # Create violation issue
                issue = Issue(
                    element_id=door.id,
                    element_type="door",
                    rule_id=rule.id,
                    message=(
                        f"""
                        Door '{door.id}' has a clear width {door.clear_width_mm:.0f} m,
                        but minimum required is {rule.min_value:.0f} mm
                        ({rule.name})
                        """
                    ),
                    code_ref=rule.code_ref,
                    severity="error"
                )
                issues.append(issue)

    return issues