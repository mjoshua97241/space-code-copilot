"""
VLM Extraction Evaluation Script

Follows RAGAS evaluation pattern to evaluate Vision LLM blueprint extraction quality.
Evaluates extraction on golden dataset (floor plan PDFs + CSV ground truth).

Usage:
    cd backend
    PYTHONPATH=. python ../evaluation/vlm_evaluation.py
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Callable, Dict, List, Any, Optional
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

# Add backend and repo root to path for imports
repo_root = Path(__file__).parent.parent
backend_path = repo_root / "backend"
sys.path.insert(0, str(backend_path))
sys.path.insert(0, str(repo_root))  # For evaluation module

from app.services.blueprint_extractor import extract_rooms_from_blueprint
from app.services.design_loader import load_rooms
from app.models.domain import Room, BlueprintExtractionResult
from evaluation.vlm_extraction_metrics import (
    calculate_all_metrics,
    match_rooms,
    calculate_area_accuracy,
    calculate_recall,
    calculate_precision,
    calculate_type_match_rate,
    calculate_name_match_rate,
    calculate_semantic_understanding_score,
    calculate_confidence_calibration,
    calculate_composite_score,
)

# Optional import for Hugging Face model.
# Note: our current HF wrapper relies on Unsloth, which requires a CUDA-capable GPU.
HF_IMPORT_ERROR: Optional[str] = None
try:
    import torch
    from evaluation.hf_vlm_wrapper import create_hf_extractor
    HF_AVAILABLE = True
except Exception as e:  # ImportError or runtime errors from Unsloth on CPU-only machines
    HF_AVAILABLE = False
    HF_IMPORT_ERROR = str(e)
    torch = None


# Paths
BASE_DIR = Path(__file__).parent.parent
BACKEND_DIR = BASE_DIR / "backend"
FLOOR_PLANS_DIR = BACKEND_DIR / "app" / "data" / "floor-plans"
RESULTS_DIR = BASE_DIR / "evaluation" / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR = BASE_DIR / "evaluation" / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)


def create_golden_dataset_from_csvs(
    floor_plan_dir: Path = FLOOR_PLANS_DIR,
    csv_dir: Optional[Path] = None
) -> pd.DataFrame:
    """
    Create golden dataset by matching floor plan PDFs to CSV ground truth.
    
    Matches by filename pattern:
    - PDF: example_plan_01a.pdf
    - CSV: example_plan_01a.csv (direct match)
    
    Uses existing CSV loader: app.services.design_loader.load_rooms()
    
    Args:
        floor_plan_dir: Directory containing floor plan PDFs
        csv_dir: Directory containing CSV files (defaults to floor_plan_dir)
        
    Returns:
        DataFrame with columns: image_path, ground_truth_rooms, scale, plan_name, csv_path
    """
    if csv_dir is None:
        csv_dir = floor_plan_dir
    
    golden_data = []
    
    print(f"🔍 Scanning for floor plans in: {floor_plan_dir}")
    pdf_files = list(floor_plan_dir.glob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files")
    
    for pdf_path in pdf_files:
        plan_name = pdf_path.stem  # e.g., "example_plan_01a"
        
        # Try multiple CSV naming patterns
        csv_candidates = [
            csv_dir / f"{plan_name}.csv",  # Direct match (e.g., example_plan_01a.csv)
            csv_dir / f"{plan_name}_rooms.csv",  # With _rooms suffix
            floor_plan_dir / f"{plan_name}.csv",  # Also check floor_plan_dir
            floor_plan_dir / f"{plan_name}_rooms.csv",
        ]
        
        csv_path = None
        for candidate in csv_candidates:
            if candidate.exists():
                csv_path = candidate
                break
        
        if not csv_path:
            print(f"⚠ No CSV found for {pdf_path.name}, skipping...")
            continue
        
        # Load ground truth rooms from CSV
        try:
            ground_truth_rooms = list(load_rooms(csv_path))
            
            golden_data.append({
                'image_path': str(pdf_path),
                'ground_truth_rooms': ground_truth_rooms,  # List[Room]
                'scale': 1.0,  # Default 1:100, adjust if known
                'plan_name': plan_name,
                'csv_path': str(csv_path)
            })
            print(f"  ✓ {plan_name}: {len(ground_truth_rooms)} rooms from {csv_path.name}")
        except Exception as e:
            print(f"⚠ Error loading CSV for {pdf_path.name}: {e}")
            continue
    
    if not golden_data:
        print("❌ No golden dataset entries created!")
        return pd.DataFrame()
    
    df = pd.DataFrame(golden_data)
    print(f"\n✔ Golden dataset created: {len(df)} plans")
    return df


def save_golden_dataset(golden_df: pd.DataFrame, output_path: Optional[Path] = None):
    """
    Save golden dataset to JSON file.
    
    Converts Room objects to dicts for JSON serialization.
    
    Args:
        golden_df: DataFrame with golden dataset
        output_path: Optional output path (defaults to evaluation/data/vlm_golden_dataset.json)
    """
    if output_path is None:
        output_path = DATA_DIR / "vlm_golden_dataset.json"
    
    # Convert Room objects to dicts for JSON serialization
    dataset_dict = golden_df.to_dict(orient='records')
    for entry in dataset_dict:
        entry['ground_truth_rooms'] = [
            {
                'id': r.id,
                'name': r.name,
                'type': r.type,
                'level': r.level,
                'area_m2': r.area_m2
            }
            for r in entry['ground_truth_rooms']
        ]
    
    with open(output_path, 'w') as f:
        json.dump(dataset_dict, f, indent=2)
    
    print(f"✔ Golden dataset saved to: {output_path}")


def load_golden_dataset(input_path: Optional[Path] = None) -> pd.DataFrame:
    """
    Load golden dataset from JSON file.
    
    Converts dicts back to Room objects.
    
    Args:
        input_path: Optional input path (defaults to evaluation/data/vlm_golden_dataset.json)
        
    Returns:
        DataFrame with golden dataset
    """
    if input_path is None:
        input_path = DATA_DIR / "vlm_golden_dataset.json"
    
    if not input_path.exists():
        print(f"⚠ Golden dataset not found at {input_path}, creating from CSVs...")
        return create_golden_dataset_from_csvs()
    
    with open(input_path, 'r') as f:
        dataset_dict = json.load(f)
    
    # Convert dicts back to Room objects
    for entry in dataset_dict:
        entry['ground_truth_rooms'] = [
            Room(**r_dict) for r_dict in entry['ground_truth_rooms']
        ]
    
    df = pd.DataFrame(dataset_dict)
    print(f"✔ Golden dataset loaded: {len(df)} plans from {input_path}")
    return df


def evaluate_vlm_extraction(
    extractor_func: Callable[[str, Optional[float]], BlueprintExtractionResult],
    golden_dataset_df: pd.DataFrame,
    model_name: str = "gpt-4o",
    delay_between_extractions: float = 1.0
) -> Dict[str, Any]:
    """
    Evaluate VLM extraction using custom metrics (similar to RAGAS pattern).
    
    Args:
        extractor_func: Function that takes (image_path, scale_override) and returns BlueprintExtractionResult
        golden_dataset_df: DataFrame with columns: image_path, ground_truth_rooms, scale
        model_name: Name of VLM model being evaluated
        delay_between_extractions: Delay in seconds (for rate limiting)
        
    Returns:
        dict: Contains metrics_results, per_image_metrics, latency, model_name
    """
    print(f"\n{'='*60}")
    print(f"Evaluation: {model_name}")
    print(f"{'='*60}")
    if delay_between_extractions > 0:
        print(f"⚠ Rate limiting: {delay_between_extractions}s delay between extractions")
    
    per_image_metrics = []
    latencies = []
    
    # Run extraction for each blueprint in dataset
    for idx, row in golden_dataset_df.iterrows():
        image_path = row['image_path']
        ground_truth_rooms = row['ground_truth_rooms']
        scale = row.get('scale', 1.0)
        plan_name = row.get('plan_name', Path(image_path).stem)
        
        print(f"\n[{idx+1}/{len(golden_dataset_df)}] Processing: {plan_name}")
        
        start_time = time.time()
        
        try:
            # Run extraction
            extraction_result = extractor_func(image_path, scale)
            latency = time.time() - start_time
            latencies.append(latency)
            
            extracted_rooms = extraction_result.rooms
            
            print(f"  ✓ Extracted {len(extracted_rooms)} rooms in {latency:.2f}s")
            print(f"    Confidence: {extraction_result.confidence.overall:.2%}")
            
            # Calculate metrics for this extraction
            metrics = calculate_all_metrics(
                extracted_rooms=extracted_rooms,
                ground_truth_rooms=ground_truth_rooms,
                extraction_result=extraction_result,
                include_latency=True,
                latency_seconds=latency
            )
            
            # Add plan metadata
            metrics['plan_name'] = plan_name
            metrics['image_path'] = image_path
            metrics['extracted_count'] = len(extracted_rooms)
            metrics['ground_truth_count'] = len(ground_truth_rooms)
            
            per_image_metrics.append(metrics)
            
            # Print summary
            print(f"    Recall: {metrics['recall']:.2%}, Precision: {metrics['precision']:.2%}")
            print(f"    Area accuracy: {metrics['area_accuracy']:.2%}, Type match: {metrics['type_match_rate']:.2%}")
            
            # Add delay to respect rate limits (except after last extraction)
            if delay_between_extractions > 0 and idx < len(golden_dataset_df) - 1:
                print(f"    Waiting {delay_between_extractions}s...")
                time.sleep(delay_between_extractions)
                
        except Exception as e:
            print(f"  ✗ Extraction failed: {e}")
            latency = time.time() - start_time
            latencies.append(latency)
            # Add error entry
            per_image_metrics.append({
                'plan_name': plan_name,
                'image_path': image_path,
                'error': str(e),
                'extracted_count': 0,
                'ground_truth_count': len(ground_truth_rooms)
            })
    
    # Aggregate metrics across all extractions
    successful_metrics = [m for m in per_image_metrics if 'error' not in m]
    
    if not successful_metrics:
        print("❌ No successful extractions!")
        return {
            "model_name": model_name,
            "error": "All extractions failed",
            "per_image_metrics": per_image_metrics
        }
    
    # Calculate average metrics
    metric_keys = [
        'area_accuracy', 'recall', 'precision', 'type_match_rate',
        'name_match_rate', 'semantic_understanding_score', 'confidence_calibration'
    ]
    
    aggregated_metrics = {}
    for key in metric_keys:
        values = [m[key] for m in successful_metrics if key in m]
        if values:
            aggregated_metrics[key] = sum(values) / len(values)
    
    # Add latency
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    aggregated_metrics['avg_latency'] = avg_latency
    
    # Calculate composite score
    aggregated_metrics['composite_score'] = calculate_composite_score(aggregated_metrics)
    
    print(f"\n✔ Evaluation complete for {model_name}")
    print(f"   Average latency: {avg_latency:.2f}s")
    print(f"   Composite score: {aggregated_metrics['composite_score']:.3f}")
    
    return {
        "model_name": model_name,
        "metrics_results": aggregated_metrics,
        "per_image_metrics": per_image_metrics,
        "avg_latency": avg_latency,
        "evaluated_at": datetime.now().isoformat(),
        "golden_dataset_size": len(golden_dataset_df),
        "successful_extractions": len(successful_metrics),
        "failed_extractions": len(per_image_metrics) - len(successful_metrics)
    }


def compare_models(results: List[Dict[str, Any]]) -> None:
    """
    Compare evaluation results across multiple models.
    
    Args:
        results: List of evaluation result dictionaries
    """
    print(f"\n{'='*60}")
    print("Model Comparison")
    print(f"{'='*60}")
    
    # Create comparison table
    comparison_data = []
    for result in results:
        if 'error' in result:
            continue
        
        metrics = result['metrics_results']
        comparison_data.append({
            'Model': result['model_name'],
            'Composite Score': f"{metrics.get('composite_score', 0):.3f}",
            'Recall': f"{metrics.get('recall', 0):.2%}",
            'Precision': f"{metrics.get('precision', 0):.2%}",
            'Area Accuracy': f"{metrics.get('area_accuracy', 0):.2%}",
            'Type Match': f"{metrics.get('type_match_rate', 0):.2%}",
            'Semantic Score': f"{metrics.get('semantic_understanding_score', 0):.3f}",
            'Avg Latency': f"{metrics.get('avg_latency', 0):.2f}s"
        })
    
    if comparison_data:
        df = pd.DataFrame(comparison_data)
        print(df.to_string(index=False))
        
        # Find best model by composite score
        best_model = max(results, key=lambda r: r.get('metrics_results', {}).get('composite_score', 0))
        print(f"\n🏆 Best Model: {best_model['model_name']} (composite score: {best_model['metrics_results']['composite_score']:.3f})")
    else:
        print("⚠ No valid results to compare")


def save_results(results: List[Dict[str, Any]], output_path: Optional[Path] = None):
    """
    Save evaluation results to JSON file.
    
    Args:
        results: List of evaluation result dictionaries
        output_path: Optional output path (defaults to evaluation/results/vlm_evaluation_results.json)
    """
    if output_path is None:
        output_path = RESULTS_DIR / "vlm_evaluation_results.json"
    
    # Convert to JSON-serializable format
    serializable_results = []
    for result in results:
        serializable_result = result.copy()
        # Ensure all values are JSON-serializable
        if 'per_image_metrics' in serializable_result:
            # Already should be serializable, but ensure
            serializable_result['per_image_metrics'] = [
                {k: v for k, v in m.items() if not isinstance(v, (Room, BlueprintExtractionResult))}
                for m in serializable_result['per_image_metrics']
            ]
        serializable_results.append(serializable_result)
    
    with open(output_path, 'w') as f:
        json.dump(serializable_results, f, indent=2)
    
    print(f"\n✔ Results saved to: {output_path}")


def main():
    """
    Main evaluation script.
    
    Creates golden dataset, evaluates multiple models, compares results.
    """
    # Load environment variables from .env file
    env_path = Path(__file__).parent.parent / "backend" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
    
    print("="*60)
    print("VLM Extraction Evaluation")
    print("="*60)
    
    # Check for API key
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠ WARNING: OPENAI_API_KEY not set. Extraction will fail.")
        print("Set it with: export OPENAI_API_KEY=your_key_here")
        return
    
    # Load or create golden dataset
    print("\n📊 Loading golden dataset...")
    golden_df = load_golden_dataset()
    
    if golden_df.empty:
        print("❌ No golden dataset available. Exiting.")
        return
    
    # Save golden dataset for future use
    save_golden_dataset(golden_df)
    
    # Define extractor functions for different models
    def extractor_gpt4o(image_path: str, scale_override: float = 1.0) -> BlueprintExtractionResult:
        """Extractor function for GPT-4o"""
        return extract_rooms_from_blueprint(
            image_path=image_path,
            scale_override=scale_override,
            model_name="gpt-4o",
            provider="openai",
        )
    
    def extractor_gemini(image_path: str, scale_override: float = 1.0) -> BlueprintExtractionResult:
        """Extractor function for Gemini 2.0 Flash"""
        return extract_rooms_from_blueprint(
            image_path=image_path,
            scale_override=scale_override,
            model_name="gemini-2.0-flash",
            provider="gemini"
        )
    
    # Evaluate models
    results = []
    
    # Evaluate GPT-4o (optional - only if API key available)
    if os.getenv("OPENAI_API_KEY"):
        print("\n" + "="*60)
        print("Evaluating GPT-4o...")
        print("="*60)
        try:
            result_gpt4o = evaluate_vlm_extraction(
                extractor_func=extractor_gpt4o,
                golden_dataset_df=golden_df,
                model_name="gpt-4o",
                delay_between_extractions=1.0
            )
            results.append(result_gpt4o)
        except Exception as e:
            print(f"❌ GPT-4o evaluation failed: {e}")
    else:
        print("\n⚠ OPENAI_API_KEY not set. Skipping GPT-4o evaluation.")
    
    # Evaluate Gemini (optional - only if API key available)
    if os.getenv("GOOGLE_API_KEY"):
        print("\n" + "="*60)
        print("Evaluating Gemini 2.0 Flash...")
        print("="*60)
        try:
            result_gemini = evaluate_vlm_extraction(
                extractor_func=extractor_gemini,
                golden_dataset_df=golden_df,
                model_name="gemini-2.0-flash",
                delay_between_extractions=1.0
            )
            results.append(result_gemini)
        except Exception as e:
            print(f"❌ Gemini evaluation failed: {e}")
    else:
        print("\n⚠ GOOGLE_API_KEY not set. Skipping Gemini evaluation.")
    
    # Evaluate Hugging Face model (optional)
    if HF_AVAILABLE and torch:
        # Our current HF wrapper uses Unsloth, which requires CUDA.
        if not torch.cuda.is_available():
            print("\n⚠ Hugging Face evaluation requires a CUDA GPU (Unsloth does not run on CPU).")
            print("   Skipping Hugging Face evaluation.")
        else:
            print("\n" + "="*60)
            print("Evaluating Hugging Face FloorPlanVisionAIAdaptor...")
            print("="*60)
            print("✓ GPU available - using CUDA for inference\n")

            try:
                # Create HF extractor (loads model once)
                print("🔄 Loading Hugging Face model (this may take a moment)...")
                hf_extractor = create_hf_extractor(device="cuda")

                def extractor_hf(image_path: str, scale_override: float = 1.0) -> BlueprintExtractionResult:
                    """Extractor function for Hugging Face FloorPlanVisionAIAdaptor"""
                    return hf_extractor(image_path, scale_override)

                result_hf = evaluate_vlm_extraction(
                    extractor_func=extractor_hf,
                    golden_dataset_df=golden_df,
                    model_name="hf-floorplan-vision-adaptor",
                    delay_between_extractions=0.5
                )
                results.append(result_hf)
                print("✅ Hugging Face model evaluation completed")
            except Exception as e:
                print(f"❌ Hugging Face model evaluation failed: {e}")
                import traceback
                traceback.print_exc()
    else:
        print("\n⚠ Hugging Face evaluation not available in this environment.")
        if HF_IMPORT_ERROR:
            print(f"   Import error: {HF_IMPORT_ERROR}")
        print("   Install deps with: `uv pip install unsloth transformers torch pillow`")
        print("   And run on a CUDA-capable machine for Unsloth.")
    
    # Compare models
    if results:
        compare_models(results)
        save_results(results)
    else:
        print("\n❌ No evaluation results to save.")


if __name__ == "__main__":
    main()
