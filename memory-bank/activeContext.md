# Active Context

Current focus:

- Foundation complete: FastAPI app (`app/main.py`) is working with `/health` endpoint, CORS, static files, and template setup.
- Domain models complete: All Pydantic models (Room, Door, Rule, Issue) implemented in `app/models/domain.py`
- CSV loaders complete: `design_loader.py` with caching and validation
- Seeded rules complete: `rules_seed.py` with 4 rules ready for compliance checking
- Compliance checker complete: `compliance_checker.py` tested and working (found 2 violations as expected)
- API endpoints complete: `/api/issues` endpoint working and tested
- LLM components: Phase 2 (Hybrid Retrieval) and Phase 3 (Chat Endpoint) complete
  - `vector_store.py` supports BM25 + Dense hybrid retrieval
  - `/api/chat` endpoint working with RAG-based Q&A and citations
- ✅ **RAG Technique Validation COMPLETE** - Evaluated 4 techniques using RAGAS metrics
  - Compared: Dense-only, BM25-only, Hybrid (BM25 + Dense), Parent-Document Retrieval
  - **Result: BM25-only selected as best technique** (composite score: 0.422)
  - Evaluation notebook: `evaluation/rag_evaluation.py` with LangSmith integration
  - Results saved to: `evaluation/results/evaluation_results.json` and LangSmith dataset
- ✅ **Vector Store Updated** - `app/services/vector_store.py` now defaults to BM25-only retrieval
  - Default changed: `use_bm25_only=True` (validated best technique)
  - Backward compatible: Hybrid and dense-only still available via parameters
  - Chat endpoint (`app/api/chat.py`) updated to use BM25-only by default
  - Documentation updated with evaluation results and rationale
- ✅ **Phase 6: Frontend Implementation COMPLETE & TESTED** - Full-featured UI implemented and verified
  - HTML template (`app/templates/index.html`) with three-panel layout
  - Plan viewer displaying `plan.png` with header and overlay system
  - **Overlays**: Room and door overlays loaded from JSON, positioned absolutely over plan image
  - **Highlight behavior**: Clicking an issue highlights corresponding overlay in red with pulsing animation
  - Issues list with click handlers, severity badges, and code references
  - Chat panel with message rendering, citations display, and loading states
  - Modern CSS styling (`app/static/styles.css`) with responsive design and overlay animations
  - JavaScript for API integration, error handling, user interactions, and overlay management
  - **Testing completed** - No issues found in console or terminal
- ✅ **LLM Rule Extraction COMPLETE** - Integrated with project context filtering
  - `app/services/rule_extractor.py` - Extracts rules from PDFs using LLM with BM25-only retrieval
  - `app/models/domain.py` - Added `ProjectContext` model for filtering rules by project type
  - `app/services/rules_seed.py` - Integrated rule extraction into `get_all_rules()` with context filtering
  - **Project context filtering**: Filters out commercial, multi-story, fire exit, and accessibility rules when not applicable
  - **Results**: Reduced compliance issues from 28 to 3 by filtering irrelevant rules
  - Default context: Single-floor residential detached house (matches current MVP project)
  - Extracts 6-7 relevant rules (down from 14 without filtering)
- ✅ **Page Number Extraction & Citation Formatting COMPLETE**
  - `app/services/pdf_ingest.py` - Enhanced with document page number extraction from text (footer/header)
  - Stores both `page_pdf` (PDF reader page) and `page_document` (extracted from text) in metadata
  - Extracts page numbers from full pages before chunking for accuracy
  - Conservative validation to avoid false positives (max 2000 pages, ±100 variance check)
  - `app/api/chat.py` - Updated citations to explicitly show page type: "(PDF page)" or "(document page)"
  - Added post-processing function `_fix_citations_in_answer()` to automatically fix LLM citations
  - Updated LLM prompt to instruct including page type indicators in citations
  - **Result**: All citations now clearly indicate whether using PDF page numbers (matches PDF reader) or document page numbers (extracted from text)
- ✅ **Overlays with Highlight Behavior COMPLETE**
  - `app/static/overlays.json` - Contains room and door overlay definitions with pixel coordinates (x, y, width, height)
  - `app/templates/index.html` - JavaScript loads overlays, renders them over plan image, handles highlighting
  - `app/static/styles.css` - Overlay styling with blue base state, red highlight state (with !important), pulsing animation
  - **Room type matching**: Updated `check_room_compliance()` to match rules by room type (bedroom rules only apply to bedrooms, living rules only to living rooms)
  - **Highlight behavior**: Clicking an issue in the compliance list highlights the corresponding overlay (room or door) in red with pulsing animation
  - **Responsive**: Overlays automatically scale and reposition when window resizes
  - **Test data**: R101 area set to 8.5 m² (below 9.5 m² minimum) for demonstration
- ✅ **End-to-End Testing COMPLETE**
  - Created comprehensive test suite: `app/tests/test_e2e.py`
  - **All 16 tests passing** (100% success rate)
  - Tests cover: Health endpoint, static files, frontend template, issues endpoint, chat endpoint, PDF ingest, vector store, compliance checker, rule extraction
  - Test documentation: `app/tests/TEST_RESULTS.md` (detailed results), `app/tests/TEST_CHECKLIST.md` (manual testing guide)
  - System verified ready for deployment
- ✅ **Deployment Setup COMPLETE**
  - `backend/.env.example` - Environment variable template (OPENAI_API_KEY, optional Qdrant config)
  - `backend/railway.json` - Railway.app configuration (auto-detects Python, sets start command with PORT variable expansion fix)
  - `backend/Dockerfile` - Docker configuration (multi-stage build with uv, can deploy to Railway/Render/Fly.io)
  - `backend/.dockerignore` - Docker ignore patterns (excludes cache, venv, .env files)
  - `DEPLOYMENT.md` - Comprehensive deployment guide (Railway.app, Docker, local demo)
  - `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment checklist
  - `README.md` - Updated with deployment section (Railway.app, Docker, local instructions)
  - ✅ **Railway Deployment Fixes Applied**:
    - Fixed PORT environment variable expansion in `railway.json` (wrapped start command in shell: `sh -c '...'`)
    - Fixed API endpoint URLs in frontend (`/api/issues` → `/api/issues/`, `/api/chat` → `/api/chat/`) to match router definitions
    - Resolved 307 Temporary Redirect errors caused by trailing slash mismatch
    - Resolved Mixed Content errors (side effect of redirects)
  - ✅ **Deployed to Railway.app** - Public URL available, app working correctly

Recent changes:

- Completed `/api/issues` endpoint (`app/api/issues.py`):
  - `GET /api/issues` - Returns list of all compliance issues
  - `GET /api/issues/summary` - Returns summary statistics
  - Uses `APIRouter` pattern with proper error handling
  - Router mounted in `main.py` via `app.include_router(issues_router)`
  - Tested and working (returns 2 door violations as expected)
- Completed CSV loaders (`app/services/design_loader.py`):
  - `load_rooms()` and `load_doors()` with `@lru_cache` for performance
  - Automatic validation of door->room references
  - File modification time-based cache invalidation
  - Helper functions for filtering and lookup
- Completed compliance checker (`app/services/compliance_checker.py`):
  - `check_compliance()` - Main orchestrator function
  - `check_room_compliance()` and `check_door_compliance()` - Element-specific checkers
  - `get_compliance_summary()` - Helper for statistics
  - Returns Issue[] objects with detailed violation messages
  - Tested and working (`test_compliance_checker.py` - correctly found 2 door violations)
- Completed seeded rules (`app/services/rules_seed.py`):
  - 4 hardcoded rules: 2 room area rules, 2 door width rules
  - `get_all_rules()` function ready for LLM integration
  - Helper functions for rule filtering and lookup
  - Tested and working (`test_rules_seed.py`)
- Completed domain models (`app/models/domain.py`):
  - Room, Door, Rule, Issue models with Pydantic validation
  - Proper type hints and field constraints
  - Rule model supports both seeded and LLM-extracted rules (MVP core feature)
- Fixed import errors in `main.py` (`fastapi.responses` module)
- Added `jinja2` dependency to `pyproject.toml`
- Fixed static files path to use absolute paths via `Path(__file__).parent`
- Verified app imports and runs successfully
- Created deployment documentation (`memory-bank/deployment.md`):
  - Deployment options (Railway.app, Docker, Local)
  - Pre-deployment checklist
  - Required files and configurations
  - Environment variables documentation
  - Minimal frontend template reference
- Created presentation guide (`memory-bank/presentation.md`):
  - Problem, Solution, Architecture, Metrics, Demo sections
  - Timing: 7 minutes presentation + 3 minutes Q&A
  - Metrics implementation patterns from lessons (LangSmith, RAGAS)
  - Demo flow and checklist
  - Visual aids and preparation steps
- Created implementation plan (`memory-bank/implementationPlan.md`):
  - 2-week MVP implementation plan with 7 phases
  - Focus on hybrid retrieval (BM25 + Dense), citations, guardrails
  - Deferred advanced features (structured parsing, multi-hop, conflict resolution) to post-MVP
  - Risk mitigation strategies and dependencies documented
- **Completed Phase 2: Hybrid Retrieval** (`app/services/vector_store.py`):
  - Implemented BM25 retriever using `BM25Retriever` from `langchain_community`
  - Implemented hybrid retriever using `EnsembleRetriever` (BM25 + Dense)
  - Document storage for BM25 (stores raw documents alongside embeddings)
  - Configurable retrieval weights (default 0.5/0.5 for BM25/dense)
  - Tested and verified working (`test_vector_store.py` - successfully tested with PDF ingestion)
  - Added dependencies: `langchain-community>=0.3.0`, `rank-bm25>=0.2.2`
- **Updated Vector Store** (`app/services/vector_store.py`):
  - **Default changed to BM25-only** (validated best technique, composite score: 0.422)
  - New parameter: `use_bm25_only=True` (default) for explicit BM25-only control
  - Backward compatible: `use_hybrid=True` still works for hybrid retrieval
  - Updated docstrings with evaluation results and rationale
  - Chat endpoint (`app/api/chat.py`) updated to use BM25-only by default
- **Completed Phase 3: Chat Endpoint** (`app/api/chat.py`):
  - `POST /api/chat` endpoint with RAG-based Q&A
  - Uses BM25-only retrieval (validated best technique, composite score: 0.422)
  - Pydantic models: `ChatRequest`, `ChatResponse`, `Citation` (page field updated to string for type indicators)
  - Singleton pattern for vector store initialization (indexes PDFs on first use)
  - LLM cache setup (memory-based for MVP)
  - Citation extraction from retrieved document metadata
  - **Citation formatting**: Explicitly shows page type - "(PDF page)" or "(document page)"
  - **Post-processing**: `_fix_citations_in_answer()` automatically fixes LLM citations
  - Updated LLM prompt to instruct including page type in citations
  - Proper error handling and environment variable loading (dotenv)
  - Router mounted in `main.py` via `app.include_router(chat_router)`
  - Tested and working (successfully answers questions with citations)

**Recent LLM Component Updates:**

- ✅ **Phase 2 Complete**: `app/services/vector_store.py` now implements hybrid retrieval:
  - BM25 retriever setup using `BM25Retriever` from `langchain_community`
  - Hybrid retriever using `EnsembleRetriever` to combine BM25 + Dense
  - Document storage for BM25 (stores raw documents in addition to embeddings)
  - Configurable weights for BM25/dense (default 0.5/0.5)
  - Backward compatible: `use_hybrid=False` falls back to dense-only
  - Tested and working (`test_vector_store.py` - successfully retrieves 9 results for test query)
- ✅ **Dependencies added**: `langchain-community`, `rank-bm25` added to `pyproject.toml`
- ✅ **Test file**: `app/tests/test_vector_store.py` created and working

**Current Status:**
- `app/core/llm.py`: ✅ Complete - No changes needed
- `app/services/pdf_ingest.py`: ✅ **COMPLETE** - Enhanced with page number extraction (PDF page + document page), section extraction, and metadata preservation
- `app/services/vector_store.py`: ✅ **Updated** - Defaults to BM25-only (validated best, composite score: 0.422), hybrid and dense-only available as options
- `app/services/rule_extractor.py`: ✅ **COMPLETE** - LLM-based rule extraction with project context filtering, uses BM25-only retrieval (default, validated best)
- `app/api/chat.py`: ✅ **COMPLETE** - Chat endpoint with BM25-only retrieval, explicit page type indicators in citations, and post-processing to fix LLM citations

**Next Priority:**
1. ✅ **RAG Technique Validation COMPLETE**: Evaluated 4 techniques using RAGAS metrics
   - Compared: Dense-only, BM25-only, Hybrid (BM25 + Dense), Parent-Document Retrieval
   - **Best technique: BM25-only** (composite score: 0.422)
   - Metrics evaluated: context_precision, context_recall, answer_relevancy, latency
   - Composite scoring: 50% relevancy, 20% precision, 20% recall, 10% latency
   - Results: BM25-only outperformed hybrid, dense-only, and parent-document
   - Evaluation notebook: `evaluation/rag_evaluation.py` with save/load from LangSmith
2. ✅ **Vector Store Updated**: `app/services/vector_store.py` defaults to BM25-only
   - Default: `use_bm25_only=True` (validated best technique)
   - Chat endpoint updated to use BM25-only by default
   - Hybrid and dense-only still available via parameters (backward compatible)
3. ✅ **Phase 6: Frontend Implementation COMPLETE & TESTED**
   - HTML template with three-panel layout (left: plan + issues, right: chat)
   - Issues list with fetch, rendering, click handlers, and severity badges
   - Chat panel with form submission, message rendering, citations display
   - Modern CSS styling with responsive design and smooth animations
   - JavaScript for API integration, error handling, and user interactions
   - **Testing completed** - No issues found in console or terminal
4. ✅ **LLM Rule Extraction COMPLETE** - Integrated with project context filtering
   - Rule extraction from PDFs using LLM with BM25-only retrieval
   - Project context filtering (building type, stories, occupancy, classification)
   - Results: Reduced issues from 28 to 3 by filtering irrelevant rules
   - Default context: Single-floor residential detached house
5. ✅ **Phase 7: Testing + Deployment COMPLETE**
   - End-to-end testing: 16/16 tests passing (100% success rate)
   - Deployment files created: Dockerfile, railway.json, .env.example, .dockerignore
   - Deployment documentation: DEPLOYMENT.md, DEPLOYMENT_CHECKLIST.md
   - README.md updated with deployment section
   - ✅ **Railway deployment fixes**: PORT variable expansion, API endpoint trailing slashes
   - ✅ **Deployed to Railway.app** - Public URL working, all endpoints functional
6. ⏸️ **Presentation Preparation ON HOLD**
   - Presentation preparation plan created (`.cursor/plans/presentation_preparation_plan_3ed00397.plan.md`)
   - Deferred to focus on new feature development
7. ✅ **Multimodal Blueprint Extraction - ALL PHASES COMPLETE**
   - ✅ **Feature Complete**: Extract structured room data from blueprint images using vision LLM
   - Plan: `.cursor/plans/multimodal_blueprint_extraction_5b8750f3.plan.md` - **ALL TODOS COMPLETE**
   - **Scoped approach**: Room-only extraction (name, type, area) from curated plans, preview-only results
   - **Key differentiator**: Semantic understanding and structured extraction (not just OCR)
   - **Features**: Vision LLM support (GPT-4o, Gemini 2.0 Flash - **Gemini 2.0 Flash selected as default**), semantic room classification, dimension-aware inference, structured JSON output
   - **VLM capabilities**: Reads room labels, classifies types, associates dimensions with rooms, applies scale
   - **Integration**: Extracted data feeds into existing compliance checking pipeline
   - **Evaluation Framework**: Complete VLM metrics framework (similar to RAGAS pattern)
   - **Status**: All 6 phases complete ✅
     - ✅ Phase 1: Vision LLM support (`app/core/llm.py` - `get_vision_llm()` defaults to Gemini 2.0 Flash), blueprint extractor (`app/services/blueprint_extractor.py` defaults to Gemini 2.0 Flash), extraction models (`BlueprintExtractionResult`, `ExtractionConfidence`), unit tests (13/13 passing)
     - ✅ Phase 2: API endpoint (`POST /api/blueprint/extract` - preview-only, no CSV save, multi-page PDF support)
     - ✅ Phase 3: Frontend integration (file upload UI, drag-and-drop, preview table, JavaScript handling)
     - ✅ Phase 4: Validation & curated plan testing - **COMPLETE**
       - ✅ Enhanced validation logic (required fields, numeric ranges, type validation, confidence scoring)
       - ✅ Tested on 3 curated blueprint images with ground truth CSVs
       - ✅ Quantitative evaluation completed with metrics (recall, precision, area accuracy, type match rate)
       - ✅ Results documented in `backend/app/tests/CURATED_PLAN_TEST_RESULTS.md`
       - ✅ Ground truth CSVs created: `example_plan_01a.csv`, `example_plan_01b.csv`, `example_plan_02.csv`
       - ✅ Test script: `backend/app/tests/test_curated_plans.py` (handles multi-page PDFs, ground truth comparison)
       - ✅ Results JSON files: `curated_plan_results/*.json` (per-plan results + summary)
     - ✅ Phase 5: Dependencies & configuration - **COMPLETE** - Vision LLM dependencies documented, .env.example updated, README.md updated
     - ✅ Phase 6: VLM Metrics & Evaluation Framework - **COMPLETE**
       - ✅ Custom metrics framework (`evaluation/vlm_extraction_metrics.py` - 8 metrics: area_accuracy, recall, precision, type_match_rate, name_match_rate, semantic_understanding_score, confidence_calibration, composite_score)
       - ✅ Golden dataset creation (`evaluation/vlm_evaluation.py` - matches PDFs to CSVs, saves to `evaluation/data/vlm_golden_dataset.json`)
       - ✅ Evaluation script (`evaluation/vlm_evaluation.py` - follows RAGAS pattern, evaluates multiple models, compares results, saves to `evaluation/results/vlm_evaluation_results.json`)
       - ✅ **Model Comparison**: Evaluated GPT-4o vs Gemini 2.0 Flash
         - **Best Model: Gemini 2.0 Flash** (composite score: 0.753 vs GPT-4o's 0.743)
         - **Metrics**: Recall 69.66% vs 53.85%, Precision 70.24% vs 76.07%, Area Accuracy 66.59% vs 68.58%, Type Match 94.44% vs 100%, Latency 7.61s vs 13.53s
         - **Decision**: Updated all defaults to use Gemini 2.0 Flash
   - **Final Model Selection**: Gemini 2.0 Flash (better recall, faster, lower cost, comparable accuracy)

Todo next:

- ⏸️ **Presentation Preparation ON HOLD**:
  - Presentation preparation plan exists (`.cursor/plans/presentation_preparation_plan_3ed00397.plan.md`)
  - Deferred to focus on multimodal blueprint extraction feature
  - Will resume after blueprint extraction implementation

- ✅ **Multimodal Blueprint Extraction - ALL PHASES COMPLETE** (`.cursor/plans/multimodal_blueprint_extraction_5b8750f3.plan.md`):
  - **Phase 1**: Core extraction service (1.5-2 days) - ✅ **COMPLETE**
    - ✅ Vision LLM support (`app/core/llm.py` - `get_vision_llm()` defaults to Gemini 2.0 Flash)
    - ✅ Blueprint extractor (`app/services/blueprint_extractor.py` - defaults to Gemini 2.0 Flash, semantic room extraction, multi-page PDF support)
    - ✅ Extraction models (`BlueprintExtractionResult`, `ExtractionConfidence` in `domain.py`)
    - ✅ Unit tests (`app/tests/test_blueprint_extractor.py` - 13/13 passing)
  - **Phase 2**: API endpoint (0.5 day) - ✅ **COMPLETE** - POST /api/blueprint/extract (preview-only, no CSV save, multi-page PDF support)
  - **Phase 3**: Frontend integration (1 day) - ✅ **COMPLETE** - File upload UI, drag-and-drop, optional scale input, preview table, JavaScript handling
  - **Phase 4**: Validation & curated plan testing (1 day) - ✅ **COMPLETE**
    - ✅ Enhanced validation logic (required fields, numeric ranges, type validation, confidence scoring with heuristics)
    - ✅ Tested on 3 curated blueprint images with ground truth CSVs
    - ✅ Quantitative evaluation: Average recall 45.56%, precision 55.79%, area accuracy 65.38%, type match rate 100%
    - ✅ Results documented: `backend/app/tests/CURATED_PLAN_TEST_RESULTS.md` (297 lines, comprehensive analysis)
    - ✅ Ground truth CSVs created: `example_plan_01a.csv`, `example_plan_01b.csv`, `example_plan_02.csv` (manually created)
    - ✅ Test script: `backend/app/tests/test_curated_plans.py` (handles multi-page PDFs, ground truth comparison, JSON results export)
    - ✅ Results JSON files: `curated_plan_results/*.json` (per-plan results + summary.json)
  - **Phase 5**: Dependencies & configuration (0.5 day) - ✅ **COMPLETE** - Vision LLM dependencies documented, .env.example updated, README.md updated
  - **Phase 6**: VLM Metrics & Evaluation Framework (1-1.5 days) - ✅ **COMPLETE**
    - ✅ Custom metrics framework (`evaluation/vlm_extraction_metrics.py` - 8 metrics with fuzzy matching)
    - ✅ Golden dataset creation (`evaluation/vlm_evaluation.py` - matches PDFs to CSVs automatically)
    - ✅ Evaluation script (`evaluation/vlm_evaluation.py` - follows RAGAS pattern, model comparison)
    - ✅ **Model Selection**: Gemini 2.0 Flash selected as best model (composite score: 0.753 vs GPT-4o's 0.743)
    - ✅ **Defaults Updated**: All code updated to use Gemini 2.0 Flash as default
  - **Scoped approach**: Room-only extraction (name, type, approx_area_m2), curated plans, preview-only, simple scale assumption (1:100 default)
  - **Key focus**: Semantic understanding over geometry - VLM reads labels, classifies types, associates dimensions, produces structured JSON
  - **Final Model**: Gemini 2.0 Flash (better recall 69.66% vs 53.85%, faster 7.61s vs 13.53s, lower cost, comparable accuracy)
  - **Timeline**: All 6 phases complete (~5.5-7 days total)

- ✅ **Blueprint Extraction Testing & Dynamic Overlays** (`.cursor/plans/blueprint_extraction_testing_and_dynamic_overlays_ac96230f.plan.md`):
  - **Status**: ✅ Implementation complete (all plan todos marked completed; merge/branch steps were user-cancelled)
  - **Backend additions/changes**:
    - Added OCR deps in `backend/pyproject.toml`: `python-multipart`, `pytesseract`, `opencv-python` (OpenCV optional)
    - Added `Overlay` model and `BlueprintExtractionResult.overlays` in `app/models/domain.py`
    - Added `app/services/overlay_generator.py`:
      - OCR text positioning (`pytesseract.image_to_data`) with preprocessing + multiple PSM configs
      - Fuzzy matching via `rapidfuzz`
      - Overlay generation now highlights **room label text** (not full-room bounding boxes) for stability
      - Tesseract tessdata discovery attempts set `TESSDATA_PREFIX` when `eng.traineddata` is found
    - Added `POST /api/blueprint/extract-and-check/` in `app/api/blueprint.py`:
      - Extract rooms (VLM) → generate overlays (OCR) → run compliance → return extraction + issues + summary
  - **Frontend changes**:
    - `app/templates/index.html`:
      - Plan viewer now displays the uploaded blueprint (images via FileReader; PDFs via PDF.js)
      - Added “Check Compliance & Generate Overlays” button
      - Renders API-generated overlays and highlights non-compliant rooms
  - **Testing**:
    - Added/updated `app/tests/test_overlay_generator.py` (26 tests passing)
    - Integration path validated end-to-end via UI with sample PDFs
  - **Issues encountered (and resolution)**:
    - OCR initially returned 0 overlays due to missing Tesseract language data (`eng.traineddata`) / `TESSDATA_PREFIX`
      - Fix: install language pack (e.g., `tesseract-ocr-eng`) and/or point `TESSDATA_PREFIX` to tessdata dir
    - Whole-room bbox inference produced misaligned overlays → switched to **label-only overlays**
  - **VLM Label Overlays Implementation** (`.cursor/plans/vlm_label_overlays_7c388fc1.plan.md`):
    - **Status**: ✅ Backend complete, frontend rendering deferred to future
    - **Completed**:
      - ✅ Extended VLM prompt to request `label_bbox` (x, y, width, height) in pixel coordinates
      - ✅ Parsed and validated `label_bbox` from VLM response, created `Overlay` objects
      - ✅ Updated `POST /api/blueprint/extract-and-check/` to use VLM overlays by default (OCR as optional fallback)
      - ✅ Added comprehensive unit tests (11 new tests, all passing)
      - ✅ VLM overlays are now included in `BlueprintExtractionResult.overlays` automatically
    - **Deferred to future**:
      - Frontend rendering of VLM overlays in plan viewer (overlays are generated but not yet displayed)
      - Integration with existing overlay rendering system in `index.html`
  - **Known limitations (still open)**:
    - Some overlays are missing (OCR misses labels or matching fails)
    - Some overlays are wrong (false-positive match to unrelated OCR text)
    - VLM overlays may also have accuracy issues (bbox coordinates may not perfectly align with label text)
    - Next iteration should prioritize: OCR recall improvements, match gating, and frontend rendering integration
- ✅ **UI Improvements for Blueprint Extraction - COMPLETE** (`.cursor/plans/ui_improvements_for_blueprint_extraction_e4cee6b1.plan.md`):
  - **Status**: ✅ All 7 todos completed
  - **Completed improvements**:
    - ✅ **Empty Plan Viewer**: Replaced default `plan.png` with SVG placeholder showing "Upload a blueprint file to view the floor plan" until file is uploaded
    - ✅ **Editable Area Column**: Area values are now editable input fields; user edits are tracked in `extractedRooms` array and sent to compliance check endpoint
    - ✅ **New Compliance Endpoint**: Created `POST /api/blueprint/check-compliance/` that accepts `List[Room]` and returns issues + summary (allows re-checking with edited values)
    - ✅ **Conditional Compliance Column**: Compliance column is hidden initially (`compliance-column-hidden` class) and shown after first compliance check (`complianceChecked` flag)
    - ✅ **Hide Type/Level Columns**: Removed Type and Level columns from table header and body (data still available in room objects for compliance logic)
    - ✅ **Fix Tooltip Z-Index**: Fixed tooltip to appear above table header using:
      - `overflow: visible !important` on extraction-results, table, thead, tbody, and td elements
      - Higher z-index (99999) for tooltip `::after` pseudo-element
      - Proper stacking context setup
    - ✅ **Tooltip Width**: Increased tooltip max-width from 300px to 500px with explicit width for better readability
  - **Backend changes**:
    - `app/api/blueprint.py`: Added `POST /api/blueprint/check-compliance/` endpoint (lines 190-256)
      - Accepts `rooms: List[Room]` in JSON body
      - Calls `check_compliance()` and `get_compliance_summary()`
      - Returns `{"issues": List[Issue], "summary": dict}`
  - **Frontend changes**:
    - `app/templates/index.html`:
      - Empty plan viewer: SVG placeholder instead of default image (line 110)
      - Editable area inputs: `<input type="number">` with `blur` and `keypress` event listeners (lines 880-889)
      - Area tracking: `updateRoomArea(roomId, newArea)` function to update `extractedRooms` array (lines 925-940)
      - Compliance column visibility: `showComplianceColumn()` and `hideComplianceColumn()` functions (lines 1008-1037)
      - Removed Type/Level columns from table header (lines 193, 196) and body (lines 929, 941)
      - Tooltip CSS: Fixed z-index and overflow issues (lines 125-175)
      - Per-room compliance check: Added checkmark button for individual room compliance checking (lines 907-917, 991-1088)
      - Updated `checkComplianceAndGenerateOverlays()` to send edited room data to new endpoint (lines 1117-1176)
  - **User workflow**:
    1. User uploads blueprint → Plan viewer shows uploaded file
    2. User clicks "Extract Rooms" → Table displays with editable area column
    3. User edits area values → Changes tracked in `extractedRooms` array
    4. User clicks "Check Compliance" → Sends edited rooms to backend, compliance column appears
    5. User can click per-room check button (✓) to check individual rooms
    6. Tooltips show compliance issues on hover (wider, above table header)
  - **Timeline**: All improvements completed (~3-4 hours total)
- ✅ **UI Layout Restructure - COMPLETE**:
  - **Status**: ✅ Complete - Blueprint Extraction moved to right panel with tab toggle
  - **Changes**:
    - ✅ **Moved Blueprint Extraction to Right Panel**: Extracted the Blueprint Extraction panel from the left panel and moved it to the right panel
    - ✅ **Added Tab Toggle System**: Created tab interface in right panel with two tabs:
      - "💬 Q&A Chat" tab (default, active)
      - "🔍 Blueprint Extraction" tab
    - ✅ **Fixed Tab Visibility**: Only one tab content is visible at a time, taking full height of right panel
    - ✅ **Fixed Scrolling**: Resolved scrolling issue in Blueprint Extraction tab by:
      - Removing conflicting `overflow: visible !important` from `.extraction-content`
      - Adding `overflow-y: auto !important` to `#content-extraction .extraction-content`
      - Adding `min-height: 0` to enable proper flex scrolling
  - **Layout Structure**:
    - **Left Panel**: Now contains only the Floor Plan viewer (plan image with overlays)
    - **Right Panel**: Contains tabbed interface with:
      - Tab header with toggle buttons
      - Chat view (when Chat tab is active)
      - Extraction view (when Extraction tab is active)
  - **Frontend changes**:
    - `app/templates/index.html`:
      - Removed extraction panel from left panel (lines 197-237 removed)
      - Added tab system to right panel (lines 259-269: tab buttons, lines 271-303: chat content, lines 305-347: extraction content)
      - Added `switchTab(tabName)` function (lines 817-850) to handle tab switching
      - Added CSS for tab system (lines 179-245: tab buttons, tab content, extraction panel in tabs)
    - `app/static/styles.css`:
      - Updated `.right-panel` with `overflow: hidden` and `min-height: 0` (lines 516-521)
      - Added `#content-extraction .extraction-panel` styles (lines 144-151)
      - Added `#content-extraction .extraction-content` scrolling styles (lines 153-157)
      - Added `#content-extraction .extraction-header` flex-shrink (lines 159-161)
  - **User Experience**:
    - Left panel is now dedicated to floor plan viewing
    - Right panel provides easy switching between Q&A Chat and Blueprint Extraction
    - Each tab takes full height when active
    - Scrolling works properly in both tabs
  - **Timeline**: Completed (~1-2 hours total)

## Hugging Face VLM Evaluation (DEFERRED)

- **Status**: ⏸️ Deferred for now (no CUDA GPU available in local environment).
- **Why**: Current HF adapter uses **Unsloth** (`evaluation/hf_vlm_wrapper.py`), which requires a **CUDA-capable GPU** and fails on CPU-only machines.
- **What we have**:
  - `evaluation/hf_vlm_wrapper.py` + `evaluation/vlm_evaluation.py` code is in place.
  - `evaluation/INSTALL_HF_DEPS.md` documents CPU/GPU installation options, but **evaluation still requires GPU** due to Unsloth.
  - Added `evaluation/vlm_evaluation_colab.py` as a **Colab-friendly runner** for future GPU-based evaluation.
- **Latest run**:
  - GPT‑4o + Gemini evaluation runs locally; HF is skipped with a clear “CUDA required” message.

### Colab attempt (dependency issues)

- **Status**: Tried running the new Colab runner, but hit **dependency friction** in Colab.
- **Known issues to watch**:
  - **`transformers` vs `huggingface-hub` mismatch**: some installs pull `huggingface-hub>=1.0` which can break older/newer `transformers` expectations; pin `huggingface-hub>=0.34,<1.0` if needed.
  - **LangChain version conflicts in Colab** (observed):
    - `langchain-google-genai 4.2.0` requires `langchain-core>=1.2.5,<2.0.0`
    - `langgraph-prebuilt 1.0.6` requires `langchain-core>=1.0.0`
    - But this repo is on the **LangChain 0.3.x** line, where:
      - `langchain 0.3.27` requires `langchain-core>=0.3.72,<1.0.0`
      - `langchain-openai 0.3.35` requires `langchain-core>=0.3.78,<1.0.0`
    - Result: upgrading `langchain-core` to satisfy `langchain-google-genai` breaks `langchain`/`langchain-openai`, and keeping `langchain-core 0.3.x` breaks `langchain-google-genai 4.2.0`/`langgraph-prebuilt`.
    - **Implication**: In Colab, we must either (a) pin `langchain-google-genai`/`langgraph*` to versions compatible with LangChain 0.3.x, or (b) upgrade the whole LangChain stack to 1.x+ (larger change).
  - **CUDA wheel selection**: `torch` must match the Colab runtime CUDA version (try `cu121` first, then `cu118` if needed).
  - **Unsloth GPU requirement/import order**: Unsloth requires CUDA and is happiest when imported before `transformers`.
- **Next step (future)**: Re-run HF evaluation in Colab with GPU enabled and pinned HF deps (see `evaluation/vlm_evaluation_colab.py` docstring + `evaluation/INSTALL_HF_DEPS.md`).

## Next Task: Railway Deployment Prep + Testing

- **Goal**: Prepare and validate a clean deployment on **Railway**.
- **Scope**:
  - Confirm required env vars are documented and set in Railway (OpenAI/Gemini keys as needed, optional Qdrant).
  - Verify start command / PORT binding works reliably (no redirect/mixed-content regressions).
  - Smoke test key routes: `GET /`, `GET /health`, `POST /api/chat/`, `POST /api/blueprint/extract/` (and other active endpoints).
  - Confirm static assets + template render correctly in prod.

## Future Improvements

### Conversational Chat with Blueprint Context

- **Current State**: Chat is **stateless Q&A only** - each query is processed independently without conversation context.
- **Future Enhancement**: Add conversational chat capabilities with access to extracted room areas from uploaded blueprints.
- **Key Features**:
  - **Conversation History**: Maintain message history per session/conversation ID
  - **Blueprint Context Integration**: Chat should have access to extracted room data from uploaded blueprints
  - **Seamless Conversations**: Enable follow-up questions like "What about bathrooms?" after asking "What is the minimum bedroom area?"
  - **Context-Aware Answers**: LLM can reference specific rooms and areas from the user's uploaded blueprint
- **Implementation Considerations**:
  - Add `conversation_id` or `session_id` to track conversations
  - Store message history (in-memory, Redis, or database)
  - Include previous messages in LLM prompt
  - Pass extracted room data (from blueprint extraction) to chat context
  - Update `ChatRequest` to optionally include `conversation_id` and `message_history`
  - Frontend should maintain conversation state and send conversation ID with each message
- **Benefits**:
  - More natural conversation flow
  - Context-aware responses about user's specific blueprint
  - Better user experience for iterative compliance checking discussions