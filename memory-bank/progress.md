# Progress

## Current Status

Foundation is working. Domain models, CSV loaders, seeded rules, compliance checker, `/api/issues` endpoint, **Phase 2 (Hybrid Retrieval)**, **Phase 3 (Chat Endpoint)**, **RAG Technique Validation**, **Phase 6 (Frontend Implementation)**, **LLM Rule Extraction with Project Context Filtering**, **Overlays with Highlight Behavior**, **End-to-End Testing**, and **Deployment Setup** are complete. Evaluation results validated **BM25-only** as best technique (composite score: 0.422). **Vector store updated** to default to BM25-only retrieval. **Frontend UI complete and tested** - no issues found during testing. **Rule extraction integrated** with project context filtering (reduced issues from 28 to 3 by filtering commercial/multi-story rules). **Overlays implemented** - room and door overlays with red highlight on issue selection, room type-specific rule matching. **End-to-end testing complete** - 16/16 tests passed (100% success rate). **Deployment files created** - Dockerfile, railway.json, .env.example, .dockerignore, DEPLOYMENT.md, DEPLOYMENT_CHECKLIST.md. Ready to proceed with actual deployment to Railway.app and presentation prep.

## What Works

- FastAPI app (`app/main.py`):
  - `/health` endpoint returning `{"status": "ok"}`
  - CORS middleware configured
  - Static files mount at `/static/` (using absolute paths)
  - Template setup for `GET /` → `index.html`
  - App imports and runs successfully
- Domain models (`app/models/domain.py`):
  - `Room` model (id, name, type, level, area_m2)
  - `Door` model (id, location_room_id, clear_width_mm, level)
  - `Rule` model (id, name, rule_type, element_type, min_value, rule_text, code_ref)
  - `Issue` model (element_id, element_type, rule_id, message, code_ref, severity)
  - `ProjectContext` model (building_type, number_of_stories, occupancy, building_classification, requires_accessibility, requires_fire_rated)
  - All models use Pydantic with proper validation and type hints
- CSV loaders (`app/services/design_loader.py`):
  - `load_rooms()` - Loads rooms from CSV with `@lru_cache` for performance
  - `load_doors()` - Loads doors from CSV with validation of room references
  - `load_design()` - Combined loader with automatic validation
  - File modification time-based cache invalidation
  - Helper functions for filtering and lookup
- Seeded rules (`app/services/rules_seed.py`):
  - `get_seeded_rules()` - Returns 4 hardcoded rules (2 room area, 2 door width)
  - `get_all_rules()` - **COMPLETE** - Combines seeded + LLM-extracted rules with project context filtering
  - `get_default_project_context()` - Returns default context for single-floor residential detached house
  - Helper functions: `get_rules_for_element_type()`, `get_rules_by_type()`, `get_rule_by_id()`
  - Rules include: minimum bedroom area (9.5 m²), living room area (12.0 m²), accessible door width (800 mm), standard door width (700 mm)
- Compliance checker (`app/services/compliance_checker.py`):
  - `check_compliance()` - Main function that checks rooms and doors against rules
  - `check_room_compliance()` - Checks individual rooms against area_min rules with type-specific matching (bedroom rules only apply to bedrooms, living rules only to living rooms)
  - `check_door_compliance()` - Checks individual doors against width_min rules
  - `get_compliance_summary()` - Helper for issue statistics
  - Returns Issue[] objects with detailed violation messages
  - Tested and working (`test_compliance_checker.py` - found 2 violations as expected)
- API endpoints:
  - `app/api/issues.py`:
    - `GET /api/issues` - Returns list of all compliance issues (Issue[])
    - `GET /api/issues/summary` - Returns summary statistics (counts by type/severity)
    - Uses `APIRouter` pattern with proper error handling (404, 400, 500)
    - Tested and working (returns 2 door violations as expected)
  - `app/api/chat.py`:
    - `POST /api/chat` - RAG-based Q&A for building code questions
    - Accepts `ChatRequest` with user query
    - Returns `ChatResponse` with answer and citations
    - Uses BM25-only retrieval (validated best technique, composite score: 0.422)
    - Extracts citations from retrieved document metadata
    - **Citation formatting**: Explicitly shows page type - "(PDF page)" or "(document page)"
    - **Post-processing**: `_fix_citations_in_answer()` automatically fixes LLM citations to include page type indicators
    - Updated LLM prompt to instruct including page type in citations
    - Singleton pattern for vector store (indexes PDFs on first use)
    - LLM cache setup for performance
    - Environment variable loading (dotenv)
    - Tested and working (successfully answers questions with citations)
  - Both routers mounted in `main.py` via `app.include_router()`
- Project structure:
  - Backend directories: `app/api/`, `app/services/`, `app/models/`, `app/core/`
  - Data files exist: `app/data/rooms.csv`, `app/data/doors.csv`, `app/data/code_sample.pdf`, `app/data/overlays.json`
  - Static assets: `app/static/plan.png`, `app/static/styles.css`, `app/static/overlays.json`
  - Template: `app/templates/index.html` - **COMPLETE** - Full-featured frontend UI with three-panel layout
  - Overlays: Room and door overlays loaded from JSON, positioned over plan image, highlight in red when issue selected
- Vector store with BM25-only retrieval (`app/services/vector_store.py`):
  - `VectorStore` class with cache-backed embeddings (OpenAI)
  - Qdrant vector store setup (in-memory for MVP)
  - **BM25-only retrieval (default, validated best)** via RAGAS evaluation:
    - BM25 retriever for exact term matching (section numbers, citations)
    - Composite score: 0.422 (best among 4 techniques evaluated)
    - Building codes benefit more from exact term matching than semantic similarity
  - **Options available**: Hybrid (BM25 + Dense) and dense-only via parameters
  - Document storage for BM25 retrieval
  - Backward compatible: hybrid and dense-only still available
  - Tested and working (`test_vector_store.py` - successfully tested with PDF)
- PDF ingest (`app/services/pdf_ingest.py`):
  - `load_pdf()` - Loads PDF using `PyMuPDFLoader`
  - `chunk_documents()` - Chunks documents using `RecursiveCharacterTextSplitter` (1000 chars, 100 overlap)
  - `ingest_pdf()` - Convenience function with enhanced metadata
  - `extract_page_number_from_text()` - Extracts document page numbers from footer/header text
  - `extract_section_number()` - Extracts section numbers using regex patterns
  - Enhanced metadata: `source`, `chunk_index`, `page_pdf` (PDF reader page), `page_document` (extracted from text), `page` (preferred: document if available, otherwise PDF), `section` (extracted section number)
- LLM wrapper (`app/core/llm.py`):
  - `get_llm()` - Provider abstraction (OpenAI, with placeholders for Gemini/Claude)
  - `setup_llm_cache()` - In-memory or SQLite caching for LLM responses
- Dependencies:
  - All required packages installed via `uv`
  - `jinja2` added for template rendering
  - `langchain-community>=0.3.0` for BM25Retriever
  - `rank-bm25>=0.2.2` for BM25 implementation

## What's Left to Build

### Backend (MVP)

- [x] `/health` endpoint
- [x] FastAPI main app (`app/main.py`) with:
  - Static files mount (`/static/`)
  - Template setup (`GET /` → `index.html`)
  - CORS middleware
- [x] CSV loaders for rooms and doors (`app/services/design_loader.py`)
- [x] Domain models: Room, Door, Rule, Issue (`app/models/domain.py`)
- [x] Seeded rules (`app/services/rules_seed.py`)
- [x] Compliance checker (`app/services/compliance_checker.py`)
- [x] `/api/issues` endpoint returning `Issue[]` (`app/api/issues.py`)
- [x] PDF ingest (`app/services/pdf_ingest.py`) - Basic functionality complete
- [x] Vector store setup (`app/services/vector_store.py`) - **BM25-only retrieval (validated best) complete**
- [x] LLM wrapper (`app/core/llm.py`) - Basic functionality complete
- [x] Rule extraction from PDFs (`app/services/rule_extractor.py`) - **COMPLETE** - LLM-based with project context filtering
- [x] `/api/chat` endpoint with RAG and citations - **COMPLETE**
- [x] API routers mounted in `main.py` (issues + chat routers)

### UI (MVP)

- [x] Basic layout in `index.html` (left viewer, bottom issues, right chat) - **COMPLETE & TESTED**
- [x] Plan viewer displaying `plan.png` - **COMPLETE & TESTED**
- [x] Overlays from JSON with highlight behavior - **COMPLETE** - Room and door overlays with red highlight on issue selection
- [x] Issues list fetching `/api/issues` and rendering - **COMPLETE & TESTED**
- [x] Chat form posting to `/api/chat` and rendering replies - **COMPLETE & TESTED**
- [x] CSS styling in `styles.css` - **COMPLETE & TESTED**

## Known Issues

None yet (project in early setup phase).

## Next Steps

1. Implement backend Phase 1-3 (complete):

   - [x] Domain models (Room, Door, Rule, Issue) in `app/models/domain.py`
   - [x] CSV loaders in `app/services/design_loader.py`
   - [x] Seeded rules in `app/services/rules_seed.py`
   - [x] Compliance checker in `app/services/compliance_checker.py`
   - [x] `/api/issues` endpoint in `app/api/issues.py`

2. ✅ Implement frontend HTML template - **COMPLETE & TESTED**:

   - [x] Layout structure (left: plan + issues, right: chat)
   - [x] Issues list with fetch, rendering, click handlers, and severity badges
   - [x] Chat panel with form submission, message rendering, and citations display
   - [x] Modern CSS styling with responsive design
   - [x] JavaScript for API integration, error handling, and user interactions
   - [x] **Testing completed** - No issues found in console or terminal

3. ✅ Add RAG pipeline and rule extraction - **COMPLETE**:
   - [x] PDF ingest
   - [x] Vector store indexing
   - [x] LLM-based rule extraction from PDFs with project context filtering
   - [x] `/api/chat` with RAG context
   - [x] Project context filtering (reduced issues from 28 to 3)

4. Implement RAG pipeline (see `memory-bank/implementationPlan.md`):
   - [x] Phase 1: PDF ingest + basic chunking (basic functionality complete, section extraction optional)
   - [x] Phase 2: Hybrid retrieval (BM25 + Dense) - **COMPLETE**
  - [x] Phase 3: LLM wrapper + chat endpoint - **COMPLETE**
  - [x] **RAG Technique Validation** - **COMPLETE** - Evaluated 4 techniques, BM25-only selected (composite score: 0.422)
  - [ ] Phase 4: Parent-child chunking (optional)
  - [ ] Phase 5: Citations + guardrails (optional)
  - [x] Phase 6: Frontend implementation - **COMPLETE & TESTED** - No issues found
  - [x] Phase 7: Testing + deployment setup - **COMPLETE** - End-to-end testing (16/16 passed), deployment files created
  - [ ] Phase 7: Actual deployment to Railway.app + presentation prep

5. ✅ End-to-End Testing - **COMPLETE**:
   - [x] Created comprehensive test suite (`app/tests/test_e2e.py`)
   - [x] All 16 tests passing (100% success rate)
   - [x] Tested: Health endpoint, static files, frontend template, issues endpoint, chat endpoint, PDF ingest, vector store, compliance checker, rule extraction
   - [x] Test documentation: `TEST_RESULTS.md`, `TEST_CHECKLIST.md`

6. ✅ Deployment Setup - **COMPLETE**:
   - [x] Created `backend/.env.example` - Environment variable template
   - [x] Created `backend/railway.json` - Railway.app configuration (fixed PORT variable expansion)
   - [x] Created `backend/Dockerfile` - Docker configuration
   - [x] Created `backend/.dockerignore` - Docker ignore patterns
   - [x] Created `DEPLOYMENT.md` - Deployment guide for assessors
   - [x] Created `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment checklist
   - [x] Updated `README.md` - Added deployment section
   - [x] **Fixed Railway deployment issues**:
     - Fixed PORT environment variable expansion in `railway.json` (wrapped in shell)
     - Fixed API endpoint URLs in frontend (added trailing slashes to match router definitions)
     - Resolved 307 redirects and Mixed Content errors
   - [x] **Deployed to Railway.app** - Public URL available for mentors/cohorts

7. Prepare for presentation (see `memory-bank/presentation.md`):
   - [ ] Implement metrics tracking (LangSmith setup, metrics endpoint) - Optional
   - [ ] Prepare demo data and test results
   - [ ] Create visual aids (architecture diagram, slides)
   - [ ] Practice 7-minute presentation flow
   - [ ] Prepare for Q&A (technical details, scalability, future enhancements)

## Future Enhancements

### User-Provided API Keys (Post-MVP)
- **Goal**: Allow users to use their own OpenAI/Gemini API keys instead of server's API key
- **Benefits**: 
  - Eliminates server costs for LLM usage
  - Prevents API key abuse
  - Allows users to choose their preferred provider (OpenAI or Gemini)
- **Implementation**:
  - Update `ChatRequest` model to accept optional `api_key` and `provider` fields
  - Update `get_llm()` function to accept optional `api_key` parameter
  - Update chat endpoint to use user-provided API key if provided
  - Add Gemini support to `app/core/llm.py`
  - Update frontend to include API key input field (optional)
  - Add clear instructions for users on where to get API keys
- **Security considerations**:
  - Use HTTPS (Railway provides automatically)
  - Don't log API keys in server logs
  - Consider rate limiting even with user keys
  - Make API key optional (fallback to server key) or required (no server costs)
