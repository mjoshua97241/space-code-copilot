# Active Context

Current focus:

- Foundation complete: FastAPI app (`app/main.py`) is working with `/health` endpoint, CORS, static files, and template setup.
- Domain models complete: All Pydantic models (Room, Door, Rule, Issue) implemented in `app/models/domain.py`
- CSV loaders complete: `design_loader.py` with caching and validation
- Seeded rules complete: `rules_seed.py` with 4 rules ready for compliance checking
- Compliance checker complete: `compliance_checker.py` tested and working (found 2 violations as expected)
- API endpoints complete: `/api/issues` endpoint working and tested
- LLM components partially implemented: Files exist but need updates for hybrid retrieval (see "Existing Files Assessment" below)
- Next: Implement hybrid retrieval (Phase 2) - update `vector_store.py` to add BM25 + hybrid retriever

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

**Existing Files Assessment (for Hybrid Retrieval Implementation):**

- `app/core/llm.py`: ✅ **Aligned** - No changes needed. LLM wrapper is provider-agnostic and works with any retriever.
- `app/services/pdf_ingest.py`: ⚠️ **Partially aligned** - Has basic chunking and metadata. Missing: section number extraction (regex for "Section X.X.X"), page numbers in metadata. Impact: Low priority, can add later.
- `app/services/vector_store.py`: ❌ **Not aligned** - Currently only has dense embeddings. **Priority 1**: Needs BM25 retriever setup and HybridRetriever class (Phase 2 core work).
- `app/services/rule_extractor.py`: ✅ **Aligned** - No changes needed. Will automatically benefit from hybrid retrieval once `vector_store.py` is updated.

**Implementation Priority:**
1. **Phase 2**: Update `vector_store.py` for hybrid retrieval (BM25 + Dense) - This is the critical path
2. **Phase 1 enhancement**: Add section number extraction to `pdf_ingest.py` (optional, nice-to-have)
3. **Phase 3**: Create chat endpoint (depends on Phase 2)

Todo next:

- Frontend HTML template (`app/templates/index.html`) with:
  - Plan viewer (plan.png + overlays) with highlight on issue selection.
  - Issues list fetching `/api/issues` and rendering via DOM manipulation.
  - Chat panel posting to `/api/chat` and rendering replies.
