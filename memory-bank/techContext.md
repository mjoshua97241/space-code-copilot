# Tech Context

Languages:

- Python 3.11+
- TypeScript + React (Vite)

Backend:

- FastAPI for HTTP API.
- uvicorn for ASGI server.
- pydantic models: Room, Door, Rule, Issue.
- LangChain + LangGraph for LLM orchestration and agents.
- OpenAI / Gemini / Claude via config env vars.
- qdrant-client for vector DB (fallback: FAISS/in-memory).

Frontend:

- React + TypeScript + Vite.
- Simple layout: left viewer, bottom issues, right chat.
- Plan viewer: <img> + absolutely positioned overlays from overlays.json.

Data layout:

- backend/app/data/rooms.csv
- backend/app/data/doors.csv
- backend/app/data/code_sample.pdf
- backend/app/data/overlays.json
- frontend/src/overlays.json (mirrors backend for viewer)

Conventions:

- Backend code under backend/app/{api,services,models,core}.
- Frontend components under frontend/src/components.
- Use env vars for API keys and external URLs.

## Lessons and reference code

Bootcamp notes and example projects are stored under:

- internal/lessons/

They are used only as reference patterns (RAG pipelines, FastAPI + LangChain glue, etc.).
They must not be cloned wholesale into backend/app or frontend/src.
