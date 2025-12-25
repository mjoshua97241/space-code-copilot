# fastapi-endpoint

# Command: /fastapi-endpoint

When I invoke `/fastapi-endpoint`, you will:

- Take the natural language description I provide.
- Propose:
  - pydantic request/response models (if needed) in app/models/.
  - a service function in app/services/\*.
  - a FastAPI route in app/api/\* using APIRouter.
- Keep code consistent with existing patterns and imports.

Prompt template:

User will write, for example:
`/fastapi-endpoint Create GET /api/issues that returns all existing Issue models from compliance_checker, using load_rooms, load_doors, seed_rules.`

You respond with:

- The files to create or modify (with paths).
- The full code for each, ready to paste.
- Short explanation of design choices.
