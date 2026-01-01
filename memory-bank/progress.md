# Progress

## Current Status

Foundation is working. Domain models, CSV loaders, seeded rules, compliance checker, `/api/issues` endpoint, and **Phase 2 (Hybrid Retrieval)** are complete. Ready to implement Phase 3 (chat endpoint) or continue with frontend.

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
  - All models use Pydantic with proper validation and type hints
- CSV loaders (`app/services/design_loader.py`):
  - `load_rooms()` - Loads rooms from CSV with `@lru_cache` for performance
  - `load_doors()` - Loads doors from CSV with validation of room references
  - `load_design()` - Combined loader with automatic validation
  - File modification time-based cache invalidation
  - Helper functions for filtering and lookup
- Seeded rules (`app/services/rules_seed.py`):
  - `get_seeded_rules()` - Returns 4 hardcoded rules (2 room area, 2 door width)
  - `get_all_rules()` - Ready for LLM integration (combines seeded + extracted)
  - Helper functions: `get_rules_for_element_type()`, `get_rules_by_type()`, `get_rule_by_id()`
  - Rules include: minimum bedroom area (9.5 m²), living room area (12.0 m²), accessible door width (800 mm), standard door width (700 mm)
- Compliance checker (`app/services/compliance_checker.py`):
  - `check_compliance()` - Main function that checks rooms and doors against rules
  - `check_room_compliance()` - Checks individual rooms against area_min rules
  - `check_door_compliance()` - Checks individual doors against width_min rules
  - `get_compliance_summary()` - Helper for issue statistics
  - Returns Issue[] objects with detailed violation messages
  - Tested and working (`test_compliance_checker.py` - found 2 violations as expected)
- API endpoints (`app/api/issues.py`):
  - `GET /api/issues` - Returns list of all compliance issues (Issue[])
  - `GET /api/issues/summary` - Returns summary statistics (counts by type/severity)
  - Uses `APIRouter` pattern with proper error handling (404, 400, 500)
  - Router mounted in `main.py` via `app.include_router(issues_router)`
  - Tested and working (returns 2 door violations as expected)
- Project structure:
  - Backend directories: `app/api/`, `app/services/`, `app/models/`, `app/core/`
  - Data files exist: `app/data/rooms.csv`, `app/data/doors.csv`, `app/data/code_sample.pdf`, `app/data/overlays.json`
  - Static assets: `app/static/plan.png`, `app/static/styles.css`
  - Template: `app/templates/index.html` (empty)
- Vector store with hybrid retrieval (`app/services/vector_store.py`):
  - `VectorStore` class with cache-backed embeddings (OpenAI)
  - Qdrant vector store setup (in-memory for MVP)
  - **Hybrid retrieval (BM25 + Dense)** using `EnsembleRetriever`:
    - BM25 retriever for exact term matching (section numbers, citations)
    - Dense embeddings for semantic similarity
    - Merged results using Reciprocal Rank Fusion (RRF)
  - Document storage for both BM25 and dense retrieval
  - Configurable retrieval weights (default 0.5/0.5)
  - Tested and working (`test_vector_store.py` - successfully tested with PDF)
- PDF ingest (`app/services/pdf_ingest.py`):
  - `load_pdf()` - Loads PDF using `PyMuPDFLoader`
  - `chunk_documents()` - Chunks documents using `RecursiveCharacterTextSplitter` (1000 chars, 100 overlap)
  - `ingest_pdf()` - Convenience function with metadata
  - Basic metadata: `source`, `chunk_index`, page numbers
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
- [x] Vector store setup (`app/services/vector_store.py`) - **Hybrid retrieval (BM25 + Dense) complete**
- [x] LLM wrapper (`app/core/llm.py`) - Basic functionality complete
- [ ] Rule extraction from PDFs (`app/services/rule_extractor.py`) - LLM-based (will use hybrid retrieval automatically)
- [ ] `/api/rag/query` endpoint (optional)
- [ ] `/api/chat` endpoint combining issues + RAG
- [x] API routers mounted in `main.py` (issues router)

### UI (MVP)

- [ ] Basic layout in `index.html` (left viewer, bottom issues, right chat)
- [ ] Plan viewer displaying `plan.png`
- [ ] (Optional) Overlays from JSON with highlight behavior
- [ ] Issues list fetching `/api/issues` and rendering
- [ ] Chat form posting to `/api/chat` and rendering replies
- [ ] CSS styling in `styles.css`

## Known Issues

None yet (project in early setup phase).

## Next Steps

1. Implement backend Phase 1-3 (complete):

   - [x] Domain models (Room, Door, Rule, Issue) in `app/models/domain.py`
   - [x] CSV loaders in `app/services/design_loader.py`
   - [x] Seeded rules in `app/services/rules_seed.py`
   - [x] Compliance checker in `app/services/compliance_checker.py`
   - [x] `/api/issues` endpoint in `app/api/issues.py`

2. Implement frontend HTML template:

   - Layout structure
   - Issues list with fetch
   - Chat panel with form
   - Basic styling

3. Add RAG pipeline and rule extraction:
   - PDF ingest
   - Vector store indexing
   - LLM-based rule extraction from PDFs
   - `/api/chat` with RAG context

4. Implement RAG pipeline (see `memory-bank/implementationPlan.md`):
   - [x] Phase 1: PDF ingest + basic chunking (basic functionality complete, section extraction optional)
   - [x] Phase 2: Hybrid retrieval (BM25 + Dense) - **COMPLETE**
   - [ ] Phase 3: LLM wrapper + chat endpoint
   - [ ] Phase 4: Parent-child chunking (optional)
   - [ ] Phase 5: Citations + guardrails
   - [ ] Phase 6: Frontend implementation
   - [ ] Phase 7: Testing + deployment + presentation prep

5. Prepare for presentation (see `memory-bank/presentation.md`):
   - [ ] Implement metrics tracking (LangSmith setup, metrics endpoint)
   - [ ] Prepare demo data and test results
   - [ ] Create visual aids (architecture diagram, slides)
   - [ ] Practice 7-minute presentation flow
   - [ ] Prepare for Q&A (technical details, scalability, future enhancements)
