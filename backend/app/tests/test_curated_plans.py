"""
Manual testing script for curated blueprint extraction.

Tests VLM extraction on known-good floor plans.
For plans without ground truth CSV, documents extraction results and limitations.

Usage:
    cd backend
    PYTHONPATH=. python app/tests/test_curated_plans.py
"""
import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.blueprint_extractor import extract_rooms_from_blueprint
from app.services.design_loader import load_rooms
from app.models.domain import Room, BlueprintExtractionResult

# Paths
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
FLOOR_PLANS_DIR = DATA_DIR / "floor-plans"
ROOMS_CSV = DATA_DIR / "rooms.csv"
RESULTS_DIR = BASE_DIR / "app" / "tests" / "curated_plan_results"
RESULTS_DIR.mkdir(exist_ok=True)

def find_ground_truth_for_plan(plan_name: str) -> Optional[Path]:
    """
    Try to find ground truth CSV for a plan.
    
    Checks multiple patterns:
    - {plan_name}.csv (direct match)
    - {plan_name}_rooms.csv
    - {plan_name}/rooms.csv
    
    Returns:
        Path to CSV if found, None otherwise
    """
    csv_candidates = [
        # Direct match (e.g., example_plan_02.csv)
        FLOOR_PLANS_DIR / f"{plan_name}.csv",
        DATA_DIR / f"{plan_name}.csv",
        # With _rooms suffix (e.g., example_plan_02_rooms.csv)
        FLOOR_PLANS_DIR / f"{plan_name}_rooms.csv",
        DATA_DIR / f"{plan_name}_rooms.csv",
        # In subdirectory
        FLOOR_PLANS_DIR / plan_name / "rooms.csv",
        DATA_DIR / plan_name / "rooms.csv",
    ]
    
    for candidate in csv_candidates:
        if candidate.exists():
            return candidate
    
    return None

def compare_rooms(extracted: List[Room], ground_truth: List[Room]) -> Dict[str, Any]:
    """
    Compare extracted rooms to ground truth and calculate metrics.
    
    Returns:
        Dictionary with comparison metrics and details
    """
    # Simple name-based matching (fuzzy matching can be added later)
    matched_pairs = []
    unmatched_extracted = []
    unmatched_ground_truth = []
    
    # Try to match extracted rooms to ground truth by name
    ground_truth_by_name = {r.name.lower().strip(): r for r in ground_truth}
    
    for ext_room in extracted:
        ext_name_lower = ext_room.name.lower().strip()
        if ext_name_lower in ground_truth_by_name:
            gt_room = ground_truth_by_name[ext_name_lower]
            matched_pairs.append((ext_room, gt_room))
            del ground_truth_by_name[ext_name_lower]
        else:
            unmatched_extracted.append(ext_room)
    
    unmatched_ground_truth = list(ground_truth_by_name.values())
    
    # Calculate metrics
    total_ground_truth = len(ground_truth)
    total_extracted = len(extracted)
    matched_count = len(matched_pairs)
    
    recall = matched_count / total_ground_truth if total_ground_truth > 0 else 0.0
    precision = matched_count / total_extracted if total_extracted > 0 else 0.0
    
    # Area accuracy for matched rooms
    area_errors = []
    for ext_room, gt_room in matched_pairs:
        if gt_room.area_m2 > 0:
            error_pct = abs(ext_room.area_m2 - gt_room.area_m2) / gt_room.area_m2
            area_errors.append(error_pct)
    
    avg_area_error = sum(area_errors) / len(area_errors) if area_errors else 1.0
    area_accuracy = max(0.0, 1.0 - avg_area_error)
    
    # Type match rate
    type_matches = sum(1 for ext, gt in matched_pairs if ext.type == gt.type)
    type_match_rate = type_matches / matched_count if matched_count > 0 else 0.0
    
    return {
        "total_ground_truth": total_ground_truth,
        "total_extracted": total_extracted,
        "matched_count": matched_count,
        "recall": recall,
        "precision": precision,
        "area_accuracy": area_accuracy,
        "avg_area_error_pct": avg_area_error * 100,
        "type_match_rate": type_match_rate,
        "matched_pairs": [
            {
                "extracted": {
                    "id": ext.id,
                    "name": ext.name,
                    "type": ext.type,
                    "area_m2": ext.area_m2
                },
                "ground_truth": {
                    "id": gt.id,
                    "name": gt.name,
                    "type": gt.type,
                    "area_m2": gt.area_m2
                },
                "area_error_pct": abs(ext.area_m2 - gt.area_m2) / gt.area_m2 * 100 if gt.area_m2 > 0 else 0
            }
            for ext, gt in matched_pairs
        ],
        "unmatched_extracted": [
            {"id": r.id, "name": r.name, "type": r.type, "area_m2": r.area_m2}
            for r in unmatched_extracted
        ],
        "unmatched_ground_truth": [
            {"id": r.id, "name": r.name, "type": r.type, "area_m2": r.area_m2}
            for r in unmatched_ground_truth
        ]
    }

def test_plan(plan_path: Path, ground_truth_csv: Optional[Path] = None, scale: float = 1.0, page_index: Optional[int] = None) -> Dict[str, Any]:
    """
    Test extraction on a single blueprint plan.
    
    Args:
        plan_path: Path to blueprint PDF/image
        ground_truth_csv: Optional path to ground truth CSV (None if not available)
        scale: Scale factor to use (default: 1.0 for 1:100)
        page_index: Optional page index (0-based) for PDFs. If None, extracts all pages combined.
    
    Returns:
        Dictionary with test results
    """
    print(f"\n{'='*60}")
    print(f"Testing: {plan_path.name}")
    print(f"{'='*60}")
    
    # Load ground truth if available
    ground_truth_rooms = None
    if ground_truth_csv and ground_truth_csv.exists():
        print(f"Loading ground truth from: {ground_truth_csv}")
        ground_truth_rooms = load_rooms(ground_truth_csv)
        print(f"✓ Loaded {len(ground_truth_rooms)} ground truth rooms")
    else:
        print("⚠ No ground truth CSV found - will document extraction only (no comparison)")
    
    try:
        # Run extraction
        page_info = f" (page {page_index})" if page_index is not None else " (all pages combined)"
        print(f"Running extraction with scale={scale}{page_info}...")
        result: BlueprintExtractionResult = extract_rooms_from_blueprint(
            image_path=plan_path,
            scale_override=scale,
            model_name="gpt-4o",  # Use GPT-4o for best results
            page_index=page_index
        )
        
        print(f"✓ Extraction completed")
        print(f"  - Extracted {len(result.rooms)} rooms")
        print(f"  - Confidence: {result.confidence.overall:.2%}")
        print(f"    * Name: {result.confidence.name_confidence:.2%}")
        print(f"    * Type: {result.confidence.type_confidence:.2%}")
        print(f"    * Area: {result.confidence.area_confidence:.2%}")
        
        # Show extracted rooms
        print(f"\nExtracted Rooms:")
        for room in result.rooms:
            print(f"  - {room.name} ({room.type}, {room.area_m2:.2f} m²)")
        
        # Compare with ground truth if available
        comparison = None
        if ground_truth_rooms:
            comparison = compare_rooms(result.rooms, ground_truth_rooms)
            
            print(f"\nComparison Results:")
            print(f"  - Ground truth rooms: {comparison['total_ground_truth']}")
            print(f"  - Extracted rooms: {comparison['total_extracted']}")
            print(f"  - Matched: {comparison['matched_count']}")
            print(f"  - Recall: {comparison['recall']:.2%}")
            print(f"  - Precision: {comparison['precision']:.2%}")
            print(f"  - Area accuracy: {comparison['area_accuracy']:.2%}")
            print(f"  - Type match rate: {comparison['type_match_rate']:.2%}")
            
            if comparison['unmatched_extracted']:
                print(f"\n  ⚠ Unmatched extracted rooms ({len(comparison['unmatched_extracted'])}):")
                for room in comparison['unmatched_extracted']:
                    print(f"    - {room['name']} ({room['type']}, {room['area_m2']:.2f} m²)")
            
            if comparison['unmatched_ground_truth']:
                print(f"\n  ⚠ Missing ground truth rooms ({len(comparison['unmatched_ground_truth'])}):")
                for room in comparison['unmatched_ground_truth']:
                    print(f"    - {room['name']} ({room['type']}, {room['area_m2']:.2f} m²)")
        
        # Return full results
        result_dict = {
            "plan_name": plan_path.stem,
            "plan_path": str(plan_path),
            "ground_truth_csv": str(ground_truth_csv) if ground_truth_csv else None,
            "has_ground_truth": ground_truth_csv is not None and ground_truth_csv.exists(),
            "page_index": page_index,
            "extraction_result": {
                "rooms": [{"id": r.id, "name": r.name, "type": r.type, "level": r.level, "area_m2": r.area_m2} for r in result.rooms],
                "confidence": {
                    "overall": result.confidence.overall,
                    "name_confidence": result.confidence.name_confidence,
                    "type_confidence": result.confidence.type_confidence,
                    "area_confidence": result.confidence.area_confidence
                },
                "scale_used": result.scale_used,
                "scale_source": result.scale_source,
                "metadata": result.extraction_metadata
            },
            "timestamp": datetime.now().isoformat()
        }
        
        if ground_truth_rooms:
            result_dict["ground_truth"] = [
                {"id": r.id, "name": r.name, "type": r.type, "level": r.level, "area_m2": r.area_m2}
                for r in ground_truth_rooms
            ]
            result_dict["comparison"] = comparison
        
        return result_dict
    
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "plan_name": plan_path.stem,
            "plan_path": str(plan_path),
            "ground_truth_csv": str(ground_truth_csv) if ground_truth_csv else None,
            "has_ground_truth": False,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }

def main():
    """Run tests on all curated plans."""
    print("="*60)
    print("Curated Blueprint Extraction Testing")
    print("="*60)
    print(f"Testing plans in: {FLOOR_PLANS_DIR}")
    print(f"\nNOTE: Ground truth CSV (rooms.csv) is for plan.png, not floor-plans/")
    print(f"      Plans without ground truth will be documented without comparison.")
    
    # Check if API keys are set
    if not os.getenv("OPENAI_API_KEY"):
        print("\n⚠ WARNING: OPENAI_API_KEY not set. Extraction will fail.")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        return
    
    # Find all PDF plans
    plan_files = list(FLOOR_PLANS_DIR.glob("*.pdf"))
    if not plan_files:
        print(f"\n⚠ No PDF files found in {FLOOR_PLANS_DIR}")
        return
    
    print(f"\nFound {len(plan_files)} plan(s) to test:")
    for plan in plan_files:
        print(f"  - {plan.name}")
    
    # Test each plan
    all_results = []
    for plan_path in sorted(plan_files):
        plan_name = plan_path.stem
        ground_truth_csv = find_ground_truth_for_plan(plan_name)
        
        result = test_plan(plan_path, ground_truth_csv, scale=1.0)
        all_results.append(result)
        
        # Save individual result
        result_file = RESULTS_DIR / f"{plan_name}_result.json"
        with open(result_file, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\n✓ Saved results to: {result_file}")
    
    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    
    successful_tests = [r for r in all_results if "error" not in r]
    failed_tests = [r for r in all_results if "error" in r]
    tests_with_ground_truth = [r for r in successful_tests if r.get("has_ground_truth", False)]
    tests_without_ground_truth = [r for r in successful_tests if not r.get("has_ground_truth", False)]
    
    print(f"Total plans tested: {len(all_results)}")
    print(f"Successful: {len(successful_tests)}")
    print(f"Failed: {len(failed_tests)}")
    print(f"With ground truth: {len(tests_with_ground_truth)}")
    print(f"Without ground truth (extraction only): {len(tests_without_ground_truth)}")
    
    if tests_with_ground_truth:
        print(f"\nAverage Metrics (plans with ground truth):")
        avg_recall = sum(r["comparison"]["recall"] for r in tests_with_ground_truth) / len(tests_with_ground_truth)
        avg_precision = sum(r["comparison"]["precision"] for r in tests_with_ground_truth) / len(tests_with_ground_truth)
        avg_area_accuracy = sum(r["comparison"]["area_accuracy"] for r in tests_with_ground_truth) / len(tests_with_ground_truth)
        avg_type_match = sum(r["comparison"]["type_match_rate"] for r in tests_with_ground_truth) / len(tests_with_ground_truth)
        
        print(f"  - Recall: {avg_recall:.2%}")
        print(f"  - Precision: {avg_precision:.2%}")
        print(f"  - Area accuracy: {avg_area_accuracy:.2%}")
        print(f"  - Type match rate: {avg_type_match:.2%}")
    
    if tests_without_ground_truth:
        print(f"\nPlans without ground truth (extraction documented):")
        for result in tests_without_ground_truth:
            room_count = len(result["extraction_result"]["rooms"])
            confidence = result["extraction_result"]["confidence"]["overall"]
            print(f"  - {result['plan_name']}: {room_count} rooms extracted, {confidence:.2%} confidence")
    
    # Save summary
    summary_file = RESULTS_DIR / "summary.json"
    with open(summary_file, "w") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "total_tests": len(all_results),
            "successful": len(successful_tests),
            "failed": len(failed_tests),
            "with_ground_truth": len(tests_with_ground_truth),
            "without_ground_truth": len(tests_without_ground_truth),
            "results": all_results
        }, f, indent=2)
    print(f"\n✓ Saved summary to: {summary_file}")
    
    print(f"\n{'='*60}")
    print("Testing complete!")
    print(f"{'='*60}")
    print("\nNext steps:")
    print("1. Review extraction results in curated_plan_results/")
    print("2. Document findings in CURATED_PLAN_TEST_RESULTS.md")
    print("3. For plans without ground truth, manually verify extraction quality")
    print("4. Consider creating ground truth CSVs for future evaluation")

if __name__ == "__main__":
    main()