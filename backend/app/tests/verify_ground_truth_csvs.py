"""
Quick verification script to test ground truth CSV loading.

Run: cd backend && PYTHONPATH=. python app/tests/verify_ground_truth_csvs.py
"""
from pathlib import Path
from app.services.design_loader import load_rooms
from app.tests.test_curated_plans import find_ground_truth_for_plan

BASE_DIR = Path(__file__).parent.parent.parent
FLOOR_PLANS_DIR = BASE_DIR / "app" / "data" / "floor-plans"

def verify_csv(plan_name: str):
    """Verify a ground truth CSV can be loaded."""
    print(f"\n{'='*60}")
    print(f"Verifying: {plan_name}")
    print(f"{'='*60}")
    
    # Find CSV
    csv_path = find_ground_truth_for_plan(plan_name)
    if not csv_path:
        print(f"❌ No CSV found for {plan_name}")
        return False
    
    print(f"✓ Found CSV: {csv_path}")
    
    # Try to load
    try:
        rooms = load_rooms(csv_path)
        print(f"✓ Successfully loaded {len(rooms)} rooms")
        
        # Show first few rooms
        print(f"\nFirst 3 rooms:")
        for room in rooms[:3]:
            print(f"  - {room.id}: {room.name} ({room.type}, level {room.level}, {room.area_m2} m²)")
        
        if len(rooms) > 3:
            print(f"  ... and {len(rooms) - 3} more")
        
        return True
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Verify all ground truth CSVs."""
    print("="*60)
    print("Ground Truth CSV Verification")
    print("="*60)
    
    # Find all PDFs to get plan names
    pdf_files = list(FLOOR_PLANS_DIR.glob("*.pdf"))
    plan_names = [f.stem for f in pdf_files]
    
    print(f"\nFound {len(plan_names)} plan(s): {', '.join(plan_names)}")
    
    results = {}
    for plan_name in sorted(plan_names):
        results[plan_name] = verify_csv(plan_name)
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    successful = sum(1 for v in results.values() if v)
    total = len(results)
    
    print(f"Total plans: {total}")
    print(f"Successful: {successful}")
    print(f"Failed: {total - successful}")
    
    if successful == total:
        print("\n✅ All ground truth CSVs are valid and can be loaded!")
    else:
        print("\n⚠ Some CSVs failed to load. Check errors above.")

if __name__ == "__main__":
    main()
