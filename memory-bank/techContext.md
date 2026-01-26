# Tech Context

Languages:

- Python 3.11+
- HTML + CSS + JavaScript (browser-native, no build toolchain)

Backend:

- FastAPI for HTTP API.
- uvicorn for ASGI server.
- jinja2 for HTML template rendering.
- pydantic models: Room, Door, Rule, Issue.
- LangChain + LangGraph for LLM orchestration and agents.
- OpenAI / Gemini / Claude via config env vars.
- Vision LLM support: Gemini 2.0 Flash (default, selected via evaluation), GPT-4o (alternative).
- qdrant-client for vector DB (fallback: FAISS/in-memory).
- Hugging Face VLM evaluation: optional; current adapter uses **Unsloth (CUDA-only)** so HF evaluation must run on a CUDA GPU (e.g., Google Colab GPU).
  - Colab note: dependency mismatches can occur and may require pinning:
    - `transformers` ↔ `huggingface-hub` (some combos require `huggingface-hub<1.0`)
    - **LangChain stack split**: this repo uses **LangChain 0.3.x** (expects `langchain-core<1.0`), but some Colab installs pull `langchain-google-genai 4.x` / `langgraph-prebuilt 1.x` which require `langchain-core>=1.0`. These cannot coexist without pinning or a full LangChain 1.x+ upgrade.

Frontend:

- Plain HTML + CSS + minimal inline JavaScript.
- Single-page UI served directly by FastAPI (`app/templates/index.html`).
- Simple layout: left viewer, bottom issues, right chat.
- Plan viewer: <img> + absolutely positioned overlays from overlays.json.
- Browser-native `fetch` API for API calls, vanilla DOM manipulation.
- No Node/npm, no React, no build toolchain.

Data layout:

- backend/app/data/rooms.csv
- backend/app/data/doors.csv
- backend/app/data/code_sample.pdf
- backend/app/data/overlays.json
- backend/app/templates/index.html (HTML template)
- backend/app/static/styles.css (CSS)
- backend/app/static/plan.png (floor plan image)
- backend/app/static/overlays.json (optional, for browser fetch)

Conventions:

- Backend code under backend/app/{api,services,models,core}.
- Frontend UI: HTML template in backend/app/templates/, CSS in backend/app/static/.
- All frontend code served by FastAPI (no separate frontend server).
- Use env vars for API keys and external URLs.

## Lessons and reference code

Bootcamp notes and example projects are stored under:

- internal/lessons/

They are used only as reference patterns (RAG pipelines, FastAPI + LangChain glue, etc.).
They must not be cloned wholesale into backend/app or frontend code.
