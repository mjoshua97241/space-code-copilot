# System Patterns

Backend patterns:

- API routes in app/api/\*.py, mounted in app/main.py via include_router.
- Services in app/services/\*.py encapsulate:
  - design_loader (CSV → Room/Door models)
  - pdf_ingest (PDF → chunks)
  - vector_store (embedding + Qdrant search)
  - compliance_checker (rules + design → issues)
  - rule_extractor (LLM-based rule extraction; stretch goal)
- LLM client abstraction in app/core/llm.py to swap OpenAI/Gemini/Claude.

AI patterns:

- Use RAG for building-code questions:
  - user query → embed → vector search over code chunks → pass snippets + question to chat model.
- Use deterministic Python for simple numeric compliance (area, widths).
- Use LLM only for:
  - summarizing issues
  - answering questions
  - extracting rules from text (phase 2).

Frontend patterns:

- App.tsx: layout + wiring (PlanViewer, IssuesList, ChatPanel).
- Components:
  - PlanViewer: loads plan.png and overlays.json; supports highlight by element_id.
  - IssuesList: fetches /api/issues and allows click to highlight element.
  - ChatPanel: posts to /api/chat and renders messages.

Plan/Act:

- For larger refactors, use PLAN first, then ACT to implement, to avoid uncontrolled code changes.

## Reusing past lessons

- internal/lessons/ may contain working examples from past bootcamp sessions.
- When generating new code for this project:
  - Prefer following the patterns defined in this file and in the current backend/frontend layout.
  - Look at internal/lessons/ only to copy small, relevant patterns (e.g., a vector_store abstraction, a LangGraph agent node) and then adapt them.
  - Do not import internal/lessons modules directly into production code.
