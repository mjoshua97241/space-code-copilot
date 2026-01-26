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
# LLM Provider (choose one for text-based operations)
OPENAI_API_KEY=your_key_here
# or
GEMINI_API_KEY=your_key_here
# or
ANTHROPIC_API_KEY=your_key_here

# Vision LLM Configuration (for blueprint extraction)
# Provider: "openai" (GPT-4o) or "gemini" (Gemini 1.5 Flash)
VISION_LLM_PROVIDER=openai

# Vision LLM API Keys (required if using vision features)
# For OpenAI (GPT-4o): Use OPENAI_API_KEY above
# For Gemini: Use GOOGLE_API_KEY below
GOOGLE_API_KEY=your_key_here  # Required if VISION_LLM_PROVIDER=gemini

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

**Implemented (MVP):**
- CSV loaders for rooms and doors
- Domain models (Room, Door, Rule, Issue)
- Compliance checker
- `/api/issues` endpoint
- PDF ingest and vector store
- `/api/chat` endpoint with RAG
- Frontend HTML template with plan viewer, issues list, and chat
- Blueprint extraction (preview) - multimodal VLM extraction from blueprint images

See `memory-bank/progress.md` for detailed status.

### Code Patterns

- **API routes**: `app/api/*.py`, mounted via `include_router` in `main.py`
- **Services**: `app/services/*.py` encapsulate business logic
- **Models**: Pydantic models in `app/models/domain.py`
- **Frontend**: Single HTML template served by FastAPI, vanilla JS for interactivity

## API Endpoints

- `GET /health` - Health check
- `GET /` - Frontend UI (HTML template)
- `GET /api/issues` - List compliance issues
- `POST /api/chat` - Chat with RAG context
- `POST /api/blueprint/extract` - Extract room data from blueprint images (preview-only)

## Blueprint Extraction (Preview)

The system includes a multimodal blueprint extraction feature that uses Vision LLMs (GPT-4o or Gemini 1.5 Flash) to extract structured room data from architectural blueprint images.

### Features

- **Semantic Understanding**: VLM reads room labels, classifies types, and associates dimensions with rooms
- **Multi-format Support**: Accepts PNG, JPG, or PDF blueprints
- **Multi-page PDFs**: Automatically combines all pages or extracts specific page
- **Structured Output**: Returns Room models (name, type, area, level) ready for compliance checking
- **Preview Mode**: Extraction results are preview-only; CSV pipeline remains ground truth

### Usage

1. Upload a blueprint image via the frontend UI (drag-and-drop or file picker)
2. Optionally specify scale factor (default: 1.0 for 1:100 scale)
3. System extracts rooms using VLM semantic understanding
4. Preview results in table with confidence scores

### Configuration

Set vision LLM provider in `.env`:

```bash
# Choose vision LLM provider
VISION_LLM_PROVIDER=openai  # or "gemini"

# API keys (required)
OPENAI_API_KEY=your_key_here  # For GPT-4o
GOOGLE_API_KEY=your_key_here  # For Gemini 1.5 Flash
```

### Limitations

- Areas are approximate (depends on scale assumption)
- Works best with clear, labeled blueprints
- Room extraction only (no door extraction in MVP)
- Preview-only results (CSV pipeline remains ground truth)

### Known Issues

- Recall: ~45% (some rooms missed, especially small spaces)
- Precision: ~56% (room splitting occurs with combined labels)
- Area accuracy: ~65% (good for matched rooms, affected by splitting)
- Type classification: 100% (excellent)

See `backend/app/tests/CURATED_PLAN_TEST_RESULTS.md` for detailed evaluation results.

## Constraints

- **Units**: Always SI units (m, m², mm). Be explicit when converting.
- **Rules**: Never invent building code rules. Use only:
  1. Seeded Rule models
  2. Text from code PDFs via RAG
- **Frontend**: No build toolchain. Plain HTML/CSS/JS served by FastAPI.

## Deployment

### Railway.app (Recommended for Demo)

1. Push your code to GitHub
2. Go to [Railway.app](https://railway.app) and sign in
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variable: `OPENAI_API_KEY` (in Railway dashboard → Variables)
6. Railway will auto-detect Python and deploy
7. Your app will be live at `https://your-app.railway.app`

**Note**: The project includes `railway.json` for automatic configuration.

### Docker

```bash
cd backend
docker build -t space-code-copilot .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key space-code-copilot
```

### Local Demo

For assessors to run locally:

```bash
# Clone repo
git clone <your-repo-url>
cd space-code-copilot/backend

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Run
uv run uvicorn app.main:app --reload

# Open http://localhost:8000
```

See `DEPLOYMENT.md` for detailed deployment instructions.

## Documentation

- `memory-bank/` - Project context, patterns, and progress tracking
- `DEPLOYMENT.md` - Deployment guide for assessors
- `docs/` - Additional documentation

## License

See `LICENSE` file.

