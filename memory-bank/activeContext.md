# Active Context

Current focus:

- Implement Phase 0–3 of the plan:
  - backend/app/main.py with /health and CORS.
  - design_loader service and basic CSV models.
  - rules_seed and compliance_checker.
  - /api/issues returning Issue[].

Todo next:

- Frontend HTML template (`app/templates/index.html`) with:
  - Plan viewer (plan.png + overlays) with highlight on issue selection.
  - Issues list fetching `/api/issues` and rendering via DOM manipulation.
  - Chat panel posting to `/api/chat` and rendering replies.
