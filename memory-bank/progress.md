# Progress

## Current Status

Foundation is working. Domain models are complete. Ready to implement CSV loaders and business logic.

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
- Project structure:
  - Backend directories: `app/api/`, `app/services/`, `app/models/`, `app/core/`
  - Data files exist: `app/data/rooms.csv`, `app/data/doors.csv`, `app/data/code_sample.pdf`, `app/data/overlays.json`
  - Static assets: `app/static/plan.png`, `app/static/styles.css`
  - Template: `app/templates/index.html` (empty)
- Dependencies:
  - All required packages installed via `uv`
  - `jinja2` added for template rendering

## What's Left to Build

### Backend (MVP)

- [x] `/health` endpoint
- [x] FastAPI main app (`app/main.py`) with:
  - Static files mount (`/static/`)
  - Template setup (`GET /` → `index.html`)
  - CORS middleware
- [ ] CSV loaders for rooms and doors (`app/services/design_loader.py`)
- [x] Domain models: Room, Door, Rule, Issue (`app/models/domain.py`)
- [ ] Seeded rules (`app/services/rules_seed.py`)
- [ ] Rule extraction from PDFs (`app/services/rule_extractor.py`) - LLM-based
- [ ] Compliance checker (`app/services/compliance_checker.py`)
- [ ] `/api/issues` endpoint returning `Issue[]`
- [ ] PDF ingest (`app/services/pdf_ingest.py`)
- [ ] Vector store setup (`app/services/vector_store.py`)
- [ ] LLM wrapper (`app/core/llm.py`)
- [ ] `/api/rag/query` endpoint (optional)
- [ ] `/api/chat` endpoint combining issues + RAG
- [ ] API routers mounted in `main.py`

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

1. Implement backend Phase 1-3:

   - Domain models (Room, Door, Rule, Issue) in `app/models/domain.py`
   - CSV loaders in `app/services/design_loader.py`
   - Seeded rules in `app/services/rules_seed.py`
   - Compliance checker in `app/services/compliance_checker.py`
   - `/api/issues` endpoint in `app/api/issues.py`

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
