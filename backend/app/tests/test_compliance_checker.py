# Quick test
import sys
from pathlib import Path

# Add backend directory to path so 'app' module can be found
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.design_loader import load_design
from app.services.compliance_checker import check_compliance

rooms, doors = load_design()

issues = check_compliance(rooms, doors)

print(f"Found {len(issues)} compliance issues:")
for issue in issues:
    print(f"- {issue.message}")
    print(f"  Code ref: {issue.code_ref}")
    print()