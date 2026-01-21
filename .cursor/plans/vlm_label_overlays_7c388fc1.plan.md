---
name: VLM Label Overlays
overview: Use the vision LLM to directly return room-label bounding boxes (pixel coordinates) alongside extracted rooms, use those boxes to create overlays, and document fallback recommendations for precise overlays if VLM boxes are unreliable.
todos:
  - id: vlm-bbox-prompt
    content: Extend VLM prompt in _build_extraction_prompt() to request per-room label_bbox (x, y, width, height) in pixel coordinates
    status: completed
  - id: vlm-bbox-parse
    content: Parse and validate label_bbox from VLM response, create Overlay objects, and populate BlueprintExtractionResult.overlays
    status: completed
    dependencies:
      - vlm-bbox-prompt
  - id: api-prefer-vlm
    content: Update POST /api/blueprint/extract-and-check/ to use VLM overlays by default (keep OCR as optional fallback)
    status: completed
    dependencies:
      - vlm-bbox-parse
  - id: tests-vlm-overlays
    content: Add/update unit tests in test_blueprint_extractor.py for VLM bbox→overlay conversion and validation
    status: pending
    dependencies:
      - vlm-bbox-parse
  - id: docs-future-overlays
    content: Add "Future Recommendations for Precise Overlays" section to memory-bank/activeContext.md documenting OCR improvements, match gating, and geometry-based approaches
    status: pending
---

## Goal

Switch overlay generation to **VLM-produced label bounding boxes** (always-on) so overlays align better than OCR+fuzzy matching, and add a short “future recommendations” section for precise overlays.

## Current State (What we’ll extend)

- VLM extraction prompt lives in [`backend/app/services/blueprint_extractor.py`](backend/app/services/blueprint_extractor.py) via `_build_extraction_prompt()` and returns JSON containing `plan_title` and `rooms`.
- The combined endpoint [`backend/app/api/blueprint.py`](backend/app/api/blueprint.py) already exposes `POST /api/blueprint/extract-and-check/` and returns `BlueprintExtractionResult` with `overlays`.
- Overlays currently come from OCR service [`backend/app/services/overlay_generator.py`](backend/app/services/overlay_generator.py) (now label-only), but still suffers from missing/wrong overlays.

## Approach

### 1) Add label-bbox schema to the VLM output

- Update `_build_extraction_prompt()` in [`backend/app/services/blueprint_extractor.py`](backend/app/services/blueprint_extractor.py) to request, for each room:
- `label_bbox`: `{ "x": int, "y": int, "width": int, "height": int }` in **image pixel coordinates**, referencing the exact image given to the VLM.
- Also ask the model to return `null` if unsure.
- Keep the existing room fields (id/name/type/level/area_m2) unchanged.

### 2) Parse label boxes into `Overlay` objects

- Extend parsing/validation in [`backend/app/services/blueprint_extractor.py`](backend/app/services/blueprint_extractor.py):
- If `label_bbox` is present and valid, create an `Overlay` for that room id with those coordinates.
- Set `room_name`/`room_type` on overlays.
- Store overlays in `BlueprintExtractionResult.overlays`.
- Add light validation:
- Clamp boxes to image bounds if needed.
- Reject boxes that are zero/negative or absurdly large (e.g., cover >50% of image) to reduce obvious hallucinations.

### 3) Update API to use VLM overlays (always)

- In [`backend/app/api/blueprint.py`](backend/app/api/blueprint.py) `POST /api/blueprint/extract-and-check/`:
- Prefer VLM overlays from the extraction result.
- Keep OCR overlay generation behind a flag (or keep it as optional debug path), but **default to VLM overlays** as requested.

### 4) Frontend remains mostly unchanged

- [`backend/app/templates/index.html`](backend/app/templates/index.html) already renders overlays from API response; no behavioral change needed beyond ensuring it uses the returned overlays.

### 5) Tests

- Update/add unit tests in [`backend/app/tests/test_blueprint_extractor.py`](backend/app/tests/test_blueprint_extractor.py) to cover:
- VLM response with `label_bbox` produces overlays.
- VLM response missing/invalid `label_bbox` yields no overlay for that room (graceful).

### 6) Add “Future Recommendations for Precise Overlays” (doc)

- Add a short section in [`memory-bank/activeContext.md`](memory-bank/activeContext.md) (and/or `README.md`) documenting next accuracy improvements:
- OCR improvements: higher PDF render DPI, rotated-text handling, region-of-interest OCR.
- Match gating: reject dimension-like tokens, 1:1 matching, top-k review UI.
- Geometry: line/wall detection + segmentation, or interactive correction tooling.

## Key Files

- [`backend/app/services/blueprint_extractor.py`](backend/app/services/blueprint_extractor.py)
- [`backend/app/api/blueprint.py`](backend/app/api/blueprint.py)
- [`backend/app/models/domain.py`](backend/app/models/domain.py)
- [`backend/app/templates/index.html`](backend/app/templates/index.html)
- [`backend/app/tests/test_blueprint_extractor.py`](backend/app/tests/test_blueprint_extractor.py)
- [`memory-bank/activeContext.md`](memory-bank/activeContext.md)

## Implementation Todos

- **vlm-bbox-prompt**: Extend VLM prompt to request per-room `label_bbox` in pixel coordinates.
- **vlm-bbox-parse**: Parse/validate `label_bbox` and populate `BlueprintExtractionResult.overlays`.
- **api-prefer-vlm**: Update `/api/blueprint/extract-and-check/` to use VLM overlays by default.
- **tests-vlm-overlays**: Add/update tests for bbox→overlay behavior.
- **docs-future-overlays**: Add future recommendations section for precise overlays.