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
