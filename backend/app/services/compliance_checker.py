from typing import List

from app.models.domain import Rule, Room, Issue

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