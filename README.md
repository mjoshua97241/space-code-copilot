# Code-Aware Space Planning Copilot

A tool to help architects and designers check early space planning (rooms, doors, corridors) against building codes and internal standards, without relying on full BIM.

## Overview

This MVP focuses on a single floor plan workflow:
- Parse CSV schedules (rooms, doors) into structured models
- Load building code PDFs, chunk, embed, and store in vector DB
- Run compliance checks against seeded rules
- Provide chat interface with RAG over code PDFs and current issues

## Tech Stack

**Backend:**
- Python 3.11+
- FastAPI + uvicorn
- LangChain + LangGraph for LLM orchestration
- Qdrant for vector storage (FAISS fallback)
- OpenAI/Gemini/Claude via config

**Frontend:**
- Plain HTML + CSS + vanilla JavaScript
- Single-page UI served directly by FastAPI
- No Node/npm, no React, no build toolchain

## Quick Start

### Prerequisites

- Python 3.11 or 3.12
- [uv](https://github.com/astral-sh/uv) package manager

### Setup

1. Install dependencies:
```bash
cd backend
uv sync
```

2. Set up environment variables (create `.env` in `backend/`):
```bash
# LLM Provider (choose one)
OPENAI_API_KEY=your_key_here
# or
GEMINI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here

# Qdrant (optional, defaults to in-memory)
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=your_key_here
```

3. Run the backend:
```bash
cd backend
uv run uvicorn app.main:app --reload
```

4. Open browser: `http://localhost:8000`

## Project Structure

```
backend/
├── app/
│   ├── api/          # FastAPI route handlers
│   ├── services/     # Business logic (CSV loaders, compliance checker, RAG)
│   ├── models/       # Pydantic domain models (Room, Door, Rule, Issue)
│   ├── core/         # LLM client abstraction, config
│   ├── data/         # Input files (CSV schedules, PDFs, overlays.json)
│   ├── static/       # Static assets (plan.png, styles.css)
│   ├── templates/    # HTML templates (index.html)
│   └── main.py       # FastAPI app entry point
├── pyproject.toml    # Dependencies (uv)
└── uv.lock          # Lock file

memory-bank/          # Project documentation and context
docs/                 # Additional documentation
```

## Data Files

Place your project data in `backend/app/data/`:

- `rooms.csv` - Room schedule (id, name, type, level, area_m2)
- `doors.csv` - Door schedule (id, location_room_id, clear_width_mm, level)
- `code_sample.pdf` - Building code PDFs
- `overlays.json` - Room/door polygon overlays for plan viewer

## Development

### Current Status

**Implemented:**
- Basic FastAPI app with `/health` endpoint
- Static file serving and template setup
- Project structure initialized

**In Progress (MVP):**
- CSV loaders for rooms and doors
- Domain models (Room, Door, Rule, Issue)
- Compliance checker
- `/api/issues` endpoint
- PDF ingest and vector store
- `/api/chat` endpoint with RAG
- Frontend HTML template with plan viewer, issues list, and chat

See `memory-bank/progress.md` for detailed status.

### Code Patterns

- **API routes**: `app/api/*.py`, mounted via `include_router` in `main.py`
- **Services**: `app/services/*.py` encapsulate business logic
- **Models**: Pydantic models in `app/models/domain.py`
- **Frontend**: Single HTML template served by FastAPI, vanilla JS for interactivity

## API Endpoints

- `GET /health` - Health check
- `GET /` - Frontend UI (HTML template)
- `GET /api/issues` - List compliance issues (planned)
- `POST /api/chat` - Chat with RAG context (planned)

## Constraints

- **Units**: Always SI units (m, m², mm). Be explicit when converting.
- **Rules**: Never invent building code rules. Use only:
  1. Seeded Rule models
  2. Text from code PDFs via RAG
- **Frontend**: No build toolchain. Plain HTML/CSS/JS served by FastAPI.

## Documentation

- `memory-bank/` - Project context, patterns, and progress tracking
- `docs/` - Additional documentation

## License

See `LICENSE` file.

