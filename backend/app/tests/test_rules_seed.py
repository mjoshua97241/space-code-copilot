# Quick test
import sys
from pathlib import Path

# Add backend directory to path so 'app' module can be found
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.rules_seed import get_seeded_rules, get_rules_for_element_type

# Test basic loading
rules = get_seeded_rules()
print(f"Total rules: {len(rules)}")
print(rules[0])  # Should print first rule

# Test filtering
room_rules = get_rules_for_element_type("room")
print(f"Room rules: {len(room_rules)}") # Should be 2

door_rules = get_rules_for_element_type("door")
print(f"Door rules: {len(door_rules)}") # Should be 2