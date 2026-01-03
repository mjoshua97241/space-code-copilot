"""
Test script for get_all_rules() - verifies seeded + extracted rules integration.

Run with: uv run python app/tests/test_get_all_rules.py
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
backend_dir = Path(__file__).parent.parent.parent
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Add backend directory to path so 'app' module can be found
sys.path.insert(0, str(backend_dir))

# Check for OPENAI_API_KEY
if not os.getenv("OPENAI_API_KEY"):
    print("Warning: OPENAI_API_KEY not set. Rule extraction will fail.")
    print("Set it in .env file or export it:")
    print("  export OPENAI_API_KEY='your-key-here'")
    print()

from app.services.rules_seed import get_all_rules

print("Testing get_all_rules()...")
print("=" * 50)

try:
    rules = get_all_rules()
    print(f"\nTotal rules: {len(rules)}")
    print("\nRules:")
    for rule in rules:
        rule_type_str = f" ({rule.rule_type})" if rule.rule_type else ""
        min_val_str = f" - min: {rule.min_value}" if rule.min_value else ""
        print(f"  - {rule.id}: {rule.name}{rule_type_str}{min_val_str}")
        if rule.code_ref:
            print(f"    Code ref: {rule.code_ref}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()