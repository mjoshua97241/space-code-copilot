---
name: Multimodal Blueprint Extraction (Scoped)
overview: Add multimodal AI capability to extract room-level data (name + approx_area_m2) from curated blueprint images (PNG/JPG/PDF). CSV pipeline remains as ground truth. Preview-only extraction results. Simple scale assumption (1:100 default). Focus on proving concept with curated plans, acknowledge limitations for general use.
todos:
  - id: vision-llm-support
    content: Add vision LLM support to app/core/llm.py (GPT-4o and Gemini 1.5 Flash Vision)
    status: pending
  - id: blueprint-extractor
    content: Create app/services/blueprint_extractor.py with room-only extraction (name + approx_area_m2), simple scale assumption, and basic validation
    status: pending
    dependencies:
      - vision-llm-support
  - id: extraction-models
    content: Add BlueprintExtractionResult and ExtractionConfidence models to app/models/domain.py (rooms only, no doors)
    status: pending
  - id: upload-endpoint
    content: Create POST /api/blueprint/extract endpoint in app/api/blueprint.py (preview-only, no CSV save)
    status: pending
    dependencies:
      - blueprint-extractor
      - extraction-models
  - id: frontend-upload-ui
    content: Add file upload UI to app/templates/index.html with drag-and-drop, optional scale input, and preview display
    status: pending
    dependencies:
      - upload-endpoint
  - id: frontend-js
    content: Add JavaScript for handling file upload, displaying extraction results in preview table
    status: pending
    dependencies:
      - frontend-upload-ui
  - id: validation-logic
    content: Implement basic validation (required fields, numeric ranges) and simple confidence scoring in blueprint_extractor.py
    status: pending
    dependencies:
      - blueprint-extractor
  - id: curated-plan-testing
    content: Test on 2-3 curated blueprint images (known-good plans), document results and limitations
    status: pending
    dependencies:
      - blueprint-extractor
      - validation-logic
  - id: dependencies-config
    content: Update pyproject.toml, .env.example, and documentation for vision LLM support
    status: pending
    dependencies:
      - vision-llm-support
  - id: vlm-metrics-framework
    content: Create evaluation/vlm_extraction_metrics.py with custom metrics (area_accuracy, recall, precision, geometry_understanding_score, confidence_calibration)
    status: pending
    dependencies:
      - blueprint-extractor
      - curated-plan-testing
  - id: vlm-evaluation-script
    content: Create evaluation/vlm_evaluation.py following RAGAS pattern - evaluate extraction on golden dataset from backend/app/data/floor-plans/
    status: pending
    dependencies:
      - vlm-metrics-framework
      - curated-plan-testing
  - id: golden-dataset-creation
    content: Create golden dataset by matching floor plan PDFs (backend/app/data/floor-plans/) to CSV ground truth data
    status: pending
    dependencies:
      - curated-plan-testing
---

# Multimodal Blueprint Extraction Implementation Plan

## Overview

Add multimodal AI capability to extract **room-level data only** (name + approximate area) from **curated architectural blueprint images** using **geometry understanding with scale**. The Vision LLM analyzes the blueprint's visual geometry (room boundaries, shapes, dimensions) and applies scale to calculate real-world areas - not just text extraction (OCR). This is a proof-of-concept feature that demonstrates the value of vision-based extraction while keeping the CSV pipeline as the reliable ground truth.

**Scoped Approach:**

1. Extract **rooms only** (name + approx_area_m2) - no door extraction
2. Work with **curated plans** (2-3 known-good blueprints) - not general purpose
3. **Preview-only** extraction results - CSV pipeline remains primary
4. **Simple scale assumption** (1:100 default, optional manual input) - no complex auto-detection
5. **Acknowledge limitations** - demo shows concept, not perfection

## Phase 6: VLM Metrics & Evaluation Framework (1-1.5 days)

Following the RAGAS evaluation pattern, create a comprehensive metrics framework to evaluate VLM extraction quality on the curated floor plans.

### 6.1 Create VLM Extraction Metrics Framework

**New file**: `evaluation/vlm_extraction_metrics.py`

**Purpose**: Define custom metrics for VLM extraction evaluation, similar to RAGAS metrics but tailored for structured data extraction.

**Metrics to implement**:

1. **Area Accuracy** (`calculate_area_accuracy`)

            - Mean Absolute Percentage Error (MAPE) for room areas
            - Matches extracted rooms to ground truth by name/id
            - Returns accuracy score: `1.0 - MAPE` (clamped to [0, 1])
            - Target: >90% accuracy for curated plans

2. **Name Match Rate** (`calculate_name_match_rate`)

            - Percentage of extracted rooms with matching names (exact or fuzzy)
            - Uses string matching with fuzzy fallback
            - Returns: `matched_count / total_ground_truth_rooms`

3. **Type Match Rate** (`calculate_type_match_rate`)

            - Percentage of extracted rooms with matching types
            - Compares room.type field (bedroom, living, etc.)
            - Returns: `matched_count / total_ground_truth_rooms`

4. **Recall** (`calculate_recall`)

            - Percentage of ground truth rooms that were found
            - Formula: `matched_rooms / total_ground_truth_rooms`
            - Measures completeness of extraction

5. **Precision** (`calculate_precision`)

            - Percentage of extracted rooms that are valid (match ground truth)
            - Formula: `matched_rooms / total_extracted_rooms`
            - Measures quality of extraction (fewer false positives)

6. **Geometry Understanding Score** (`calculate_geometry_understanding_score`)

            - Evaluates if LLM used geometry understanding vs just text extraction
            - Heuristic: geometry-based extraction produces approximate areas (within 20% of ground truth)
            - Text extraction would either be exact (if labels exist) or way off
            - Returns score based on error distribution pattern

7. **Confidence Calibration** (`calculate_confidence_calibration`)

            - Measures how well confidence scores correlate with actual accuracy
            - Compares `ExtractionConfidence` scores to actual extraction errors
            - Uses correlation coefficient or calibration error metric

8. **Composite Score** (`calculate_composite_score`)

            - Weighted combination of all metrics
            - Weights: area_accuracy (30%), recall (20%), precision (20%), geometry_understanding (15%), confidence_calibration (10%), latency (5%)
            - Provides single score for model comparison

**Key functions**:

```python
def match_rooms(extracted: List[Room], ground_truth: List[Room]) -> List[tuple]:
    """Match extracted rooms to ground truth rooms by name/id"""
    # Fuzzy matching logic
    # Returns list of (extracted_room, ground_truth_room) pairs

def calculate_area_accuracy(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate area accuracy using MAPE"""
    # Match rooms, calculate percentage errors, return 1.0 - MAPE

def calculate_recall(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate recall: % of ground truth rooms found"""

def calculate_precision(extracted_rooms: List[Room], ground_truth_rooms: List[Room]) -> float:
    """Calculate precision: % of extracted rooms that are valid"""

def calculate_geometry_understanding_score(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """Evaluate if LLM used geometry understanding vs text extraction"""

def calculate_confidence_calibration(
    extracted_rooms: List[Room],
    ground_truth_rooms: List[Room],
    extraction_result: BlueprintExtractionResult
) -> float:
    """Measure confidence score calibration"""

def calculate_composite_score(metrics: Dict[str, float]) -> float:
    """Calculate weighted composite score for model comparison"""
```

### 6.2 Create Golden Dataset

**New file**: `evaluation/data/vlm_golden_dataset.csv` (or JSON)

**Purpose**: Create ground truth dataset by matching floor plan PDFs to their corresponding CSV files.

**Structure**:

- `image_path`: Path to blueprint PDF (e.g., `backend/app/data/floor-plans/example_plan_01.pdf`)
- `ground_truth_rooms`: JSON string or list of Room objects (from CSV)
- `scale`: Known scale for blueprint (default: 1.0 for 1:100)
- `plan_name`: Identifier (e.g., "example_plan_01")
- `metadata`: Additional info (floor level, building type, etc.)

**Implementation**:

```python
# evaluation/vlm_evaluation.py (helper function)

def create_golden_dataset_from_csvs(
    floor_plan_dir: Path,
    csv_dir: Path
) -> pd.DataFrame:
    """
    Create golden dataset by matching floor plan PDFs to CSV ground truth.
    
    Matches by filename pattern:
 - PDF: example_plan_01.pdf
 - CSV: example_plan_01_rooms.csv (or rooms.csv in subdirectory)
    
    Uses existing CSV loader: app.services.design_loader.load_rooms()
    """
    from app.services.design_loader import load_rooms
    
    golden_data = []
    
    for pdf_path in floor_plan_dir.glob("*.pdf"):
        plan_name = pdf_path.stem  # e.g., "example_plan_01"
        
        # Try multiple CSV naming patterns
        csv_candidates = [
            csv_dir / f"{plan_name}_rooms.csv",
            csv_dir / f"{plan_name}/rooms.csv",
            csv_dir / "rooms.csv"  # Fallback
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
        except Exception as e:
            print(f"⚠ Error loading CSV for {pdf_path.name}: {e}")
            continue
    
    return pd.DataFrame(golden_data)
```

**Note**: For serialization, convert `List[Room]` to JSON string when saving to CSV, parse back when loading.

### 6.3 Create VLM Evaluation Script

**New file**: `evaluation/vlm_evaluation.py`

**Purpose**: Main evaluation script following RAGAS pattern - evaluates VLM extraction on golden dataset.

**Structure** (similar to `evaluation/rag_evaluation.py`):

1. **Load/Create Golden Dataset**

            - Load from `evaluation/data/vlm_golden_dataset.csv` if exists
            - Otherwise, create from `backend/app/data/floor-plans/` and CSV files
            - Convert Room objects to/from JSON for CSV serialization

2. **Evaluation Function** (`evaluate_vlm_extraction`)

            - Takes extractor function, golden dataset, model name
            - Runs extraction on each blueprint in dataset
            - Calculates metrics for each extraction
            - Aggregates metrics across all blueprints
            - Returns results dictionary

3. **Model Comparison**

            - Evaluate multiple models (GPT-4o, Gemini 1.5 Flash)
            - Compare metrics side-by-side
            - Calculate composite scores
            - Save results to JSON/CSV

4. **Results Display**

            - Print comparison table
            - Show per-image metrics
            - Highlight best model by composite score
            - Save results to `evaluation/results/vlm_evaluation_results.json`

**Key function**:

```python
def evaluate_vlm_extraction(
    extractor_func: Callable,
    golden_dataset_df: pd.DataFrame,
    model_name: str = "gpt-4o",
    delay_between_extractions: float = 1.0
) -> Dict:
    """
    Evaluate VLM extraction using custom metrics (similar to RAGAS pattern)
    
    Args:
        extractor_func: Function that takes (image_path, scale_override) and returns BlueprintExtractionResult
        golden_dataset_df: DataFrame with columns: image_path, ground_truth_rooms, scale
        model_name: Name of VLM model being evaluated
        delay_between_extractions: Delay in seconds (for rate limiting)
    
    Returns:
        dict: Contains metrics_results, per_image_metrics, latency, model_name
    """
    # Run extraction for each blueprint
    # Calculate metrics for each extraction
    # Aggregate metrics
    # Return results
```

**Usage example**:

```python
# Evaluate GPT-4o
def extractor_gpt4o(image_path, scale_override=1.0):
    from app.services.blueprint_extractor import extract_rooms_from_blueprint
    return extract_rooms_from_blueprint(
        image_path=image_path,
        scale_override=scale_override,
        model_name="gpt-4o"
    )

results_gpt4o = evaluate_vlm_extraction(
    extractor_func=extractor_gpt4o,
    golden_dataset_df=golden_df,
    model_name="gpt-4o",
    delay_between_extractions=1.0
)
```

### 6.4 Integration with Existing Evaluation Structure

**File structure**:

```
evaluation/
├── rag_evaluation.py          # Existing RAG evaluation
├── vlm_evaluation.py          # NEW: VLM extraction evaluation
├── vlm_extraction_metrics.py # NEW: Custom metrics
├── data/
│   ├── golden_dataset.csv           # Existing RAG golden dataset
│   └── vlm_golden_dataset.csv       # NEW: VLM golden dataset
└── results/
    ├── rag_evaluation_results.csv   # Existing RAG results
    └── vlm_evaluation_results.json  # NEW: VLM results
```

**Dependencies**:

- Use existing `datasets` library (already in dependencies for RAGAS)
- Use existing `pandas` for data manipulation
- Reuse CSV loader from `app.services.design_loader`

### 6.5 Testing Strategy

**Test cases**:

1. **Metrics calculation tests** (`test_vlm_extraction_metrics.py`)

            - Test `match_rooms()` with various room name patterns
            - Test `calculate_area_accuracy()` with known errors
            - Test `calculate_recall()` and `calculate_precision()`
            - Test `calculate_geometry_understanding_score()` heuristic
            - Test `calculate_composite_score()` weighting

2. **Golden dataset creation tests**

            - Test matching PDFs to CSVs by filename
            - Test CSV loading and Room object creation
            - Test serialization/deserialization of Room objects

3. **Evaluation script tests**

            - Test `evaluate_vlm_extraction()` with mock extractor
            - Test metrics aggregation
            - Test results saving/loading

4. **Integration tests**

            - Test full evaluation pipeline on curated plans
            - Verify metrics match expected values
            - Compare results across models

### 6.6 Expected Results

**Metrics targets for curated plans**:

- **Area Accuracy**: >90% (MAPE < 10%)
- **Recall**: >80% (finds most rooms)
- **Precision**: >85% (few false positives)
- **Geometry Understanding Score**: >0.7 (demonstrates geometry measurement)
- **Composite Score**: >0.75 (overall quality)

**Output format**:

```json
{
  "model": "gpt-4o",
  "area_accuracy": 0.92,
  "name_match_rate": 0.95,
  "type_match_rate": 0.90,
  "recall": 0.85,
  "precision": 0.88,
  "geometry_understanding_score": 0.78,
  "confidence_calibration": 0.72,
  "avg_latency": 8.5,
  "composite_score": 0.84,
  "evaluated_at": "2024-01-15T10:30:00",
  "golden_dataset_size": 2
}
```

### 6.7 Timeline

- **6.1 Metrics Framework**: 0.5 day (implement all metric functions)
- **6.2 Golden Dataset**: 0.25 day (create dataset from floor plans + CSVs)
- **6.3 Evaluation Script**: 0.5 day (main evaluation function + comparison)
- **6.4 Testing**: 0.25 day (unit tests for metrics)

**Total**: 1-1.5 days