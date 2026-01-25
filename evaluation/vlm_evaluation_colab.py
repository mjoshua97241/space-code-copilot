"""
Colab-friendly VLM Extraction Evaluation Script
================================================

This is a Colab-ready version of `evaluation/vlm_evaluation.py`.

Key differences vs the original:
- Does NOT require `cd backend` or `uv run ...`.
- Lets you point to the repo root explicitly (`--repo-root`) if needed.
- Adds repo root + backend to `sys.path` internally.
- Lets you enable/disable model runs via flags, and only runs API models when keys exist.
- Handles Hugging Face evaluation in Colab by requiring CUDA (GPU) and importing `unsloth`
  *before* importing transformers-dependent code paths to avoid Unsloth warnings.

Typical Colab usage (in notebook cells):

1) Clone repo:
   !git clone <your-repo-url> space-code-copilot
   %cd /content/space-code-copilot

2) Install deps (minimal set for evaluation):
   !pip -q install -U pip
   !pip -q install -U "pydantic>=2.7,<3" "pymupdf>=1.24,<2" pillow pandas python-dotenv rapidfuzz
   !pip -q install -U "openai>=1.40,<2" "langchain>=0.3,<0.4" "langchain-openai>=0.3,<0.4"
   !pip -q install -U "langchain-google-genai>=0.1.0"

   # HF (GPU) - choose ONE torch index matching your Colab runtime CUDA:
   # Most Colab GPUs work with cu121 nowadays; if it fails, switch to cu118.
   !pip -q install -U torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
   !pip -q install -U "huggingface-hub>=0.34,<1.0" transformers unsloth bitsandbytes

3) Set keys (only needed for the model(s) you run):
   import os
   os.environ["OPENAI_API_KEY"] = "..."
   os.environ["GOOGLE_API_KEY"] = "..."   # for Gemini

4) Run:
   !python evaluation/vlm_evaluation_colab.py --run-openai --run-gemini --run-hf
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
from dotenv import load_dotenv


def _add_paths(repo_root: Path) -> None:
    """Ensure repo_root and backend are importable."""
    repo_root = repo_root.resolve()
    backend_path = repo_root / "backend"
    sys.path.insert(0, str(backend_path))
    sys.path.insert(0, str(repo_root))


def _resolve_repo_root(explicit: Optional[str]) -> Path:
    """
    Resolve repo root for Colab/CLI.

    Defaults to:
    - --repo-root if provided
    - else: two levels up from this file (evaluation/ -> repo root)
    """
    if explicit:
        return Path(explicit).expanduser().resolve()
    return Path(__file__).resolve().parent.parent


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def load_golden_dataset(data_dir: Path) -> pd.DataFrame:
    """
    Load golden dataset from evaluation/data/vlm_golden_dataset.json.
    """
    from app.models.domain import Room  # local import after sys.path setup

    input_path = data_dir / "vlm_golden_dataset.json"
    if not input_path.exists():
        raise FileNotFoundError(
            f"Golden dataset not found at {input_path}. "
            f"Generate it first (or ensure repo data files are present)."
        )

    with open(input_path, "r") as f:
        dataset_dict = json.load(f)

    for entry in dataset_dict:
        entry["ground_truth_rooms"] = [Room(**r) for r in entry["ground_truth_rooms"]]

    df = pd.DataFrame(dataset_dict)
    print(f"✔ Golden dataset loaded: {len(df)} plans from {input_path}")
    return df


def save_results(results: List[Dict[str, Any]], results_dir: Path) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"vlm_evaluation_results_{_timestamp()}.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    return out_path


def evaluate_vlm_extraction(
    extractor_func: Callable[[str, float], "BlueprintExtractionResult"],
    golden_dataset_df: pd.DataFrame,
    model_name: str,
    delay_between_extractions: float = 1.0,
) -> Dict[str, Any]:
    """
    Evaluate VLM extraction using the existing metrics framework.
    (Logic mirrors evaluation/vlm_evaluation.py.)
    """
    from app.models.domain import BlueprintExtractionResult  # noqa: F401
    from evaluation.vlm_extraction_metrics import calculate_all_metrics

    print("\n" + "=" * 60)
    print(f"Evaluation: {model_name}")
    print("=" * 60)
    print(f"⚠ Rate limiting: {delay_between_extractions:.1f}s delay between extractions")

    per_image_metrics: List[Dict[str, Any]] = []
    latencies: List[float] = []

    successful = 0
    failed = 0

    for idx, row in golden_dataset_df.iterrows():
        plan_name = row.get("plan_name", f"plan_{idx}")
        image_path = row["image_path"]
        scale = float(row.get("scale", 1.0))
        ground_truth_rooms = row["ground_truth_rooms"]

        print(f"\n[{idx+1}/{len(golden_dataset_df)}] Processing: {plan_name}")
        start = time.time()
        try:
            result = extractor_func(image_path, scale)
            latency = time.time() - start
            latencies.append(latency)
            successful += 1

            extracted_rooms = result.rooms
            metrics = calculate_all_metrics(
                extracted_rooms=extracted_rooms,
                ground_truth_rooms=ground_truth_rooms,
                latency_seconds=latency,
                confidence=getattr(result, "confidence", None),
            )
            metrics.update(
                {
                    "plan_name": plan_name,
                    "image_path": image_path,
                    "extracted_count": len(extracted_rooms),
                    "ground_truth_count": len(ground_truth_rooms),
                }
            )
            per_image_metrics.append(metrics)

            print(f"  ✓ Extracted {len(extracted_rooms)} rooms in {latency:.2f}s")
            print(f"    Recall: {metrics['recall']*100:.2f}%, Precision: {metrics['precision']*100:.2f}%")
            print(f"    Area accuracy: {metrics['area_accuracy']*100:.2f}%, Type match: {metrics['type_match_rate']*100:.2f}%")
        except Exception as e:
            latency = time.time() - start
            latencies.append(latency)
            failed += 1

            per_image_metrics.append(
                {
                    "plan_name": plan_name,
                    "image_path": image_path,
                    "error": str(e),
                    "extracted_count": 0,
                    "ground_truth_count": len(ground_truth_rooms),
                }
            )
            print(f"  ✗ Extraction failed: {e}")

        if idx < len(golden_dataset_df) - 1:
            print(f"    Waiting {delay_between_extractions:.1f}s...")
            time.sleep(delay_between_extractions)

    # Aggregate only successful metric rows
    metric_rows = [m for m in per_image_metrics if "error" not in m]
    if not metric_rows:
        print("❌ No successful extractions!")
        return {
            "model_name": model_name,
            "metrics_results": {},
            "per_image_metrics": per_image_metrics,
            "avg_latency": sum(latencies) / max(1, len(latencies)),
            "evaluated_at": datetime.now().isoformat(),
            "golden_dataset_size": len(golden_dataset_df),
            "successful_extractions": successful,
            "failed_extractions": failed,
        }

    # Average metrics across successful extractions
    keys = [
        "area_accuracy",
        "recall",
        "precision",
        "type_match_rate",
        "name_match_rate",
        "semantic_understanding_score",
        "confidence_calibration",
        "avg_latency",
        "composite_score",
    ]
    metrics_results: Dict[str, Any] = {}
    for k in keys:
        vals = [m[k] for m in metric_rows if k in m]
        if vals:
            metrics_results[k] = float(sum(vals) / len(vals))

    avg_latency = float(sum(latencies) / max(1, len(latencies)))
    metrics_results["avg_latency"] = avg_latency

    print(f"\n✔ Evaluation complete for {model_name}")
    print(f"   Average latency: {avg_latency:.2f}s")
    if "composite_score" in metrics_results:
        print(f"   Composite score: {metrics_results['composite_score']:.3f}")

    return {
        "model_name": model_name,
        "metrics_results": metrics_results,
        "per_image_metrics": per_image_metrics,
        "avg_latency": avg_latency,
        "evaluated_at": datetime.now().isoformat(),
        "golden_dataset_size": len(golden_dataset_df),
        "successful_extractions": successful,
        "failed_extractions": failed,
    }


def compare_models(results: List[Dict[str, Any]]) -> None:
    if not results:
        print("\n❌ No evaluation results to compare.")
        return

    rows = []
    for r in results:
        m = r.get("metrics_results", {}) or {}
        rows.append(
            {
                "Model": r.get("model_name"),
                "Composite Score": m.get("composite_score"),
                "Recall": m.get("recall"),
                "Precision": m.get("precision"),
                "Area Accuracy": m.get("area_accuracy"),
                "Type Match": m.get("type_match_rate"),
                "Semantic Score": m.get("semantic_understanding_score"),
                "Avg Latency": m.get("avg_latency"),
                "Success": f"{r.get('successful_extractions', 0)}/{r.get('golden_dataset_size', 0)}",
            }
        )

    df = pd.DataFrame(rows)
    # nicer formatting for display
    def pct(x: Any) -> Any:
        return None if x is None else f"{float(x)*100:.2f}%"

    for col in ["Recall", "Precision", "Area Accuracy", "Type Match"]:
        df[col] = df[col].apply(pct)

    if "Composite Score" in df.columns:
        df["Composite Score"] = df["Composite Score"].apply(lambda x: None if x is None else f"{float(x):.3f}")
    if "Avg Latency" in df.columns:
        df["Avg Latency"] = df["Avg Latency"].apply(lambda x: None if x is None else f"{float(x):.2f}s")

    print("\n" + "=" * 60)
    print("Model Comparison")
    print("=" * 60)
    print(df.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=None, help="Path to repo root (defaults to inferred)")
    parser.add_argument("--run-openai", action="store_true", help="Run GPT-4o evaluation (requires OPENAI_API_KEY)")
    parser.add_argument("--run-gemini", action="store_true", help="Run Gemini evaluation (requires GOOGLE_API_KEY)")
    parser.add_argument("--run-hf", action="store_true", help="Run HF evaluation (requires CUDA GPU + HF deps)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between extractions (seconds)")
    args = parser.parse_args()

    repo_root = _resolve_repo_root(args.repo_root)
    _add_paths(repo_root)

    # Load .env if present (helpful locally; in Colab env vars are usually set in-notebook)
    load_dotenv(repo_root / "backend" / ".env", override=False)

    from app.services.blueprint_extractor import extract_rooms_from_blueprint

    base_dir = repo_root
    data_dir = base_dir / "evaluation" / "data"
    results_dir = base_dir / "evaluation" / "results"

    print("=" * 60)
    print("VLM Extraction Evaluation (Colab)")
    print("=" * 60)

    print("\n📊 Loading golden dataset...")
    golden_df = load_golden_dataset(data_dir)

    results: List[Dict[str, Any]] = []

    # GPT-4o (OpenAI)
    if args.run_openai:
        if os.getenv("OPENAI_API_KEY"):
            def extractor_gpt4o(image_path: str, scale_override: float = 1.0):
                return extract_rooms_from_blueprint(
                    image_path=image_path,
                    scale_override=scale_override,
                    model_name="gpt-4o",
                    provider="openai",
                )

            print("\n" + "=" * 60)
            print("Evaluating GPT-4o...")
            print("=" * 60)
            results.append(
                evaluate_vlm_extraction(
                    extractor_func=extractor_gpt4o,
                    golden_dataset_df=golden_df,
                    model_name="gpt-4o",
                    delay_between_extractions=args.delay,
                )
            )
        else:
            print("\n⚠ OPENAI_API_KEY not set. Skipping GPT-4o evaluation.")

    # Gemini
    if args.run_gemini:
        if os.getenv("GOOGLE_API_KEY"):
            def extractor_gemini(image_path: str, scale_override: float = 1.0):
                return extract_rooms_from_blueprint(
                    image_path=image_path,
                    scale_override=scale_override,
                    model_name="gemini-2.0-flash",
                    provider="gemini",
                )

            print("\n" + "=" * 60)
            print("Evaluating Gemini 2.0 Flash...")
            print("=" * 60)
            results.append(
                evaluate_vlm_extraction(
                    extractor_func=extractor_gemini,
                    golden_dataset_df=golden_df,
                    model_name="gemini-2.0-flash",
                    delay_between_extractions=args.delay,
                )
            )
        else:
            print("\n⚠ GOOGLE_API_KEY not set. Skipping Gemini evaluation.")

    # Hugging Face (GPU/Colab)
    if args.run_hf:
        hf_available = False
        hf_import_error: Optional[str] = None

        try:
            import torch  # noqa: F401
            if not torch.cuda.is_available():
                hf_import_error = "CUDA not available. Colab HF eval requires GPU runtime."
            else:
                # Unsloth recommends importing it before transformers.
                import unsloth  # noqa: F401
                from evaluation.hf_vlm_wrapper import create_hf_extractor
                hf_available = True
        except Exception as e:
            hf_import_error = str(e)

        if not hf_available:
            print("\n⚠ Hugging Face evaluation not available.")
            if hf_import_error:
                print(f"   Reason: {hf_import_error}")
            print("   Tip: In Colab, set Runtime -> Change runtime type -> GPU")
        else:
            print("\n" + "=" * 60)
            print("Evaluating Hugging Face FloorPlanVisionAIAdaptor...")
            print("=" * 60)

            # Load once (can take a while)
            hf_extractor = create_hf_extractor(device="cuda")

            def extractor_hf(image_path: str, scale_override: float = 1.0):
                return hf_extractor(image_path, scale_override)

            # HF runs slower; reduce batching risk, keep a small delay
            results.append(
                evaluate_vlm_extraction(
                    extractor_func=extractor_hf,
                    golden_dataset_df=golden_df,
                    model_name="hf-floorplan-vision-adaptor",
                    delay_between_extractions=max(args.delay, 0.5),
                )
            )

    # Summarize + save
    compare_models(results)
    out_path = save_results(results, results_dir)
    print(f"\n✔ Results saved to: {out_path}")


if __name__ == "__main__":
    main()

