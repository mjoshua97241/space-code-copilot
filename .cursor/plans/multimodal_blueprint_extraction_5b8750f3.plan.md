---
name: Multimodal Blueprint Extraction (Scoped)
overview: Add multimodal AI capability to extract structured room data (name, type, area) from curated blueprint images using semantic understanding and structured extraction. VLM interprets room labels, classifies types, reads dimensions, and produces structured JSON. CSV pipeline remains as ground truth. Preview-only extraction results. Focus on proving multimodal LLM integration and structured pipeline (blueprint → structured data → code issues).
todos:
  - id: vision-llm-support
    content: Add vision LLM support to app/core/llm.py (GPT-4o and Gemini 1.5 Flash Vision)
    status: completed
  - id: blueprint-extractor
    content: Create app/services/blueprint_extractor.py with semantic room extraction (name, type classification, area/dimensions), structured JSON output, and basic validation
    status: completed
    dependencies:
      - vision-llm-support
  - id: extraction-models
    content: Add BlueprintExtractionResult and ExtractionConfidence models to app/models/domain.py (rooms only, no doors)
    status: completed
  - id: upload-endpoint
    content: Create POST /api/blueprint/extract endpoint in app/api/blueprint.py (preview-only, no CSV save)
    status: completed
    dependencies:
      - blueprint-extractor
      - extraction-models
  - id: frontend-upload-ui
    content: Add file upload UI to app/templates/index.html with drag-and-drop, optional scale input, and preview display
    status: completed
    dependencies:
      - upload-endpoint
  - id: frontend-js
    content: Add JavaScript for handling file upload, displaying extraction results in preview table
    status: completed
    dependencies:
      - frontend-upload-ui
  - id: validation-logic
    content: Implement basic validation (required fields, numeric ranges) and simple confidence scoring in blueprint_extractor.py
    status: completed
    dependencies:
      - blueprint-extractor
  - id: curated-plan-testing
    content: Test on 2-3 curated blueprint images (known-good plans), document results and limitations
    status: completed
    dependencies:
      - blueprint-extractor
      - validation-logic
  - id: dependencies-config
    content: Update pyproject.toml, .env.example, and documentation for vision LLM support
    status: completed
    dependencies:
      - vision-llm-support
  - id: vlm-metrics-framework
    content: Create evaluation/vlm_extraction_metrics.py with custom metrics (area_accuracy, recall, precision, type_match_rate, semantic_understanding_score, confidence_calibration)
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

