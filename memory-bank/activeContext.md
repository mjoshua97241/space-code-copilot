# Active Context

Current focus:

- Foundation complete: FastAPI app (`app/main.py`) is working with `/health` endpoint, CORS, static files, and template setup.
- Domain models complete: All Pydantic models (Room, Door, Rule, Issue) implemented in `app/models/domain.py`
- CSV loaders complete: `design_loader.py` with caching and validation
- Seeded rules complete: `rules_seed.py` with 4 rules ready for compliance checking
- Compliance checker complete: `compliance_checker.py` tested and working (found 2 violations as expected)
- API endpoints complete: `/api/issues` endpoint working and tested
- Next: Choose between frontend implementation or LLM components:
  - Frontend: HTML template with plan viewer, issues list, and chat panel
  - LLM: Rule extraction from PDFs (`app/services/rule_extractor.py`) - MVP core feature

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

Todo next:

- Frontend HTML template (`app/templates/index.html`) with:
  - Plan viewer (plan.png + overlays) with highlight on issue selection.
  - Issues list fetching `/api/issues` and rendering via DOM manipulation.
  - Chat panel posting to `/api/chat` and rendering replies.
