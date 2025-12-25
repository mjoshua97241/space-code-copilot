# Product Context

Target users:

- Architects and designers working on early-stage layouts for vertical buildings.

Primary problem:

- Manually checking room areas, door widths, and corridor widths against building codes and internal standards is slow and error-prone.

Inputs:

- Floor plan image (plan.png).
- CSV schedules:
  - rooms.csv (id, name, type, level, area_m2)
  - doors.csv (id, location_room_id, clear_width_mm, level)
- Building code PDFs (code_sample.pdf).
- overlays.json for room/door polygons on plan image.

Core features (MVP):

- Backend endpoint /api/issues:
  - loads CSVs and seeded Rule models,
  - runs compliance_checker,
  - returns Issue[] with element_id, rule_id, message, code_ref.
- Backend endpoint /api/chat:
  - combines RAG results from code PDFs with current issues,
  - answers questions about code requirements and current design issues.
- Frontend (single-page HTML/CSS/JS served directly by FastAPI):
  - Plan viewer with overlay highlighting when an issue is selected.
  - Issues list panel below viewer.
  - Chat panel on the right side.
  - No separate frontend server or build process; all served from `GET /` endpoint.

Success criteria:

- Returns correct violations for a small sample dataset.
- Chat can:
  - list current issues,
  - explain why a room/door is non-compliant,
  - quote relevant code text when available.

## Project Intent & Learning Goals

This project serves dual purposes:

1. **Bootcamp demo**: Showcase a working MVP that demonstrates AI/LLM integration in an AEC domain application.

2. **Learning project**: Deep understanding of the codebase, not just accepting AI-generated code.

**Learning objectives:**
- Understand architectural decisions and tradeoffs
- Learn patterns from `internal/lessons/` as reference examples, not templates to clone
- Build comprehension of FastAPI, LangChain/LangGraph, RAG pipelines, and vector stores
- Develop ability to reason about code structure and make informed choices

**Working style:**
- Explanations and rationale are essential when implementing features
- Break down complex patterns so they can be understood, not just copied
- Encourage questions and discussion about design decisions
- Code should be clear and well-structured to support learning