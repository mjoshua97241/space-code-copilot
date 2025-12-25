# Active Context

Current focus:

- Foundation complete: FastAPI app (`app/main.py`) is working with `/health` endpoint, CORS, static files, and template setup.
- Next: Implement Phase 1–3:
  - Domain models: Room, Door, Rule, Issue (`app/models/domain.py`)
  - CSV loaders (`app/services/design_loader.py`)
  - Seeded rules (`app/services/rules_seed.py`)
  - Rule extraction from PDFs (`app/services/rule_extractor.py`) - LLM-based (MVP core)
  - Compliance checker (`app/services/compliance_checker.py`)
  - `/api/issues` endpoint returning `Issue[]`

Recent changes:

- Fixed import errors in `main.py` (`fastapi.responses` module)
- Added `jinja2` dependency to `pyproject.toml`
- Fixed static files path to use absolute paths via `Path(__file__).parent`
- Verified app imports and runs successfully

Todo next:

- Create domain models (Room, Door, Rule, Issue) with Pydantic
- Implement CSV parsing service
- Frontend HTML template (`app/templates/index.html`) with:
  - Plan viewer (plan.png + overlays) with highlight on issue selection.
  - Issues list fetching `/api/issues` and rendering via DOM manipulation.
  - Chat panel posting to `/api/chat` and rendering replies.
