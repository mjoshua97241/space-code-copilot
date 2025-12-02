# Progress

## Current Status

Project structure is initialized with directories and empty files. Core implementation is pending.

## What Works

- Project structure:
  - Backend directories: `app/api/`, `app/services/`, `app/models/`, `app/core/`
  - Data files exist: `app/data/rooms.csv`, `app/data/doors.csv`, `app/data/code_sample.pdf`, `app/data/overlays.json`
  - Static assets: `app/static/plan.png`, `app/static/styles.css`
  - Template: `app/templates/index.html` (empty)

## What's Left to Build

### Backend (MVP)

- [ ] `/health` endpoint
- [ ] CSV loaders for rooms and doors (`app/services/design_loader.py`)
- [ ] Domain models: Room, Door, Rule, Issue (`app/models/domain.py`)
- [ ] Seeded rules (`app/services/rules_seed.py`)
- [ ] Compliance checker (`app/services/compliance_checker.py`)
- [ ] `/api/issues` endpoint returning `Issue[]`
- [ ] PDF ingest (`app/services/pdf_ingest.py`)
- [ ] Vector store setup (`app/services/vector_store.py`)
- [ ] LLM wrapper (`app/core/llm.py`)
- [ ] `/api/rag/query` endpoint (optional)
- [ ] `/api/chat` endpoint combining issues + RAG
- [ ] FastAPI main app (`app/main.py`) with:
  - Static files mount (`/static/`)
  - Template setup (`GET /` → `index.html`)
  - API routers

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

1. Implement backend Phase 0-3:

   - `/health` endpoint
   - Domain models (Room, Door, Rule, Issue)
   - CSV loaders
   - Seeded rules
   - Compliance checker
   - `/api/issues` endpoint

2. Implement frontend HTML template:

   - Layout structure
   - Issues list with fetch
   - Chat panel with form
   - Basic styling

3. Add RAG pipeline:
   - PDF ingest
   - Vector store indexing
   - `/api/chat` with RAG context
