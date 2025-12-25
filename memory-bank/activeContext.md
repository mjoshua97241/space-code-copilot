# Active Context

Current focus:

- Foundation complete: FastAPI app (`app/main.py`) is working with `/health` endpoint, CORS, static files, and template setup.
- Domain models complete: All Pydantic models (Room, Door, Rule, Issue) implemented in `app/models/domain.py`
- Next: Implement Phase 1–3:
  - CSV loaders (`app/services/design_loader.py`)
  - Seeded rules (`app/services/rules_seed.py`)
  - Rule extraction from PDFs (`app/services/rule_extractor.py`) - LLM-based (MVP core)
  - Compliance checker (`app/services/compliance_checker.py`)
  - `/api/issues` endpoint returning `Issue[]`

Recent changes:

- Completed domain models (`app/models/domain.py`):
  - Room, Door, Rule, Issue models with Pydantic validation
  - Proper type hints and field constraints
  - Rule model supports both seeded and LLM-extracted rules (MVP core feature)
- Fixed import errors in `main.py` (`fastapi.responses` module)
- Added `jinja2` dependency to `pyproject.toml`
- Fixed static files path to use absolute paths via `Path(__file__).parent`
- Verified app imports and runs successfully

Todo next:

- Implement CSV parsing service (`app/services/design_loader.py`)
- Frontend HTML template (`app/templates/index.html`) with:
  - Plan viewer (plan.png + overlays) with highlight on issue selection.
  - Issues list fetching `/api/issues` and rendering via DOM manipulation.
  - Chat panel posting to `/api/chat` and rendering replies.
