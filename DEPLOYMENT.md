# Deployment Guide for Assessors

## Quick Start (Local)

1. Clone: `git clone <repo-url>`
2. Setup: `cd backend && uv sync`
3. Configure: Copy `.env.example` to `.env`, add:
   - `GOOGLE_API_KEY` (required for blueprint extraction)
   - `OPENAI_API_KEY` (required for rule extraction and RAG chat)
4. Run: `uv run uvicorn app.main:app --reload`
5. Open: http://localhost:8000

## Railway.app Deployment (Public URL)

### Prerequisites
- GitHub account
- Railway.app account (free tier available)
- **Vision LLM API key** (required for blueprint extraction):
  - `GOOGLE_API_KEY` - For Gemini 2.0 Flash (default, recommended)
  - OR `OPENAI_API_KEY` - For GPT-4o (alternative)
- `OPENAI_API_KEY` - For text-based LLM features (rule extraction, RAG chat)

### Steps

1. **Push code to GitHub**
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Deploy to Railway**
   - Go to [Railway.app](https://railway.app) and sign in
   - Click "New Project" → "Deploy from GitHub repo"
   - Select your repository
   - Railway will auto-detect Python and start building

3. **Configure Environment Variables**
   - In Railway dashboard, go to your project → Variables
   - Add required keys:
     - `GOOGLE_API_KEY` = `your_gemini_api_key` (for blueprint extraction - Gemini 2.0 Flash is default)
     - `OPENAI_API_KEY` = `your_openai_api_key` (for rule extraction and RAG chat)
   - Optional: `VISION_LLM_PROVIDER` = `"gemini"` or `"openai"` (defaults to "gemini")
   - Railway will automatically restart the service

4. **Get Public URL**
   - Railway provides a public URL automatically (e.g., `https://your-app.railway.app`)
   - Share this URL with mentors/cohorts for testing

### Railway Configuration

The project includes `railway.json` which configures:
- Build: Uses Nixpacks (auto-detects Python)
- Start command: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Restart policy: Automatic restart on failure

## Docker Deployment (Alternative)

### Build and Run Locally

```bash
cd backend
docker build -t space-code-copilot .
docker run -p 8000:8000 -e OPENAI_API_KEY=your_key space-code-copilot
```

### Deploy to Other Platforms

The Dockerfile can be used to deploy to:
- Railway.app (supports Docker)
- Render.com
- Fly.io
- AWS ECS
- Google Cloud Run
- Azure Container Instances

## What to Test

### Health Check
- ✅ `GET /health` → `{"status": "ok"}`

### API Endpoints
- ✅ `GET /api/issues` → List of compliance issues
- ✅ `GET /api/issues/summary` → Summary statistics
- ✅ `POST /api/chat` → RAG-based chat with citations
- ✅ `POST /api/blueprint/extract/` → Extract rooms from blueprint (PNG/JPG/PDF upload)
- ✅ `POST /api/blueprint/extract-and-check/` → Extract rooms + check compliance
- ✅ `POST /api/blueprint/check-compliance/` → Re-check compliance with edited room data

### Frontend
- ✅ `GET /` → Frontend UI loads
- ✅ Issues list displays compliance violations
- ✅ Chat panel works for building code questions
- ✅ Overlays highlight on issue selection
- ✅ **Blueprint Extraction tab** (right panel):
  - File upload (PNG/JPG/PDF) works
  - Plan viewer displays uploaded blueprint
  - Room extraction table shows extracted rooms
  - Area column is editable (user can correct values)
  - Compliance column appears after first check
  - Per-room compliance check button (✓) works
  - Tooltips show compliance issues (above table header)
- ✅ **Tab toggle** between "Q&A Chat" and "Blueprint Extraction" works

### Features
- ✅ Compliance checking (rooms and doors)
- ✅ Rule extraction from PDFs (with project context filtering)
- ✅ RAG chat with citations (BM25-only retrieval, validated best)
- ✅ Overlays with highlight behavior
- ✅ **Blueprint extraction** (VLM-based):
  - Extract rooms from blueprint images (PNG/JPG/PDF)
  - Multi-page PDF support (combines pages or extracts specific page)
  - Semantic room type classification
  - Area calculation with scale factor
  - Confidence scoring
- ✅ **Interactive compliance checking**:
  - User can edit extracted room areas
  - Re-check compliance with edited values
  - Per-room compliance checking

## MVP Features

- CSV-based room/door loading
- Compliance checking against rules (seeded + LLM-extracted)
- Issue reporting via API
- LLM-based rule extraction from PDFs (with project context filtering)
- RAG chat interface for building code questions
- Frontend UI with plan viewer, issues list, and chat panel
- **Blueprint extraction** (VLM-based room extraction from images)
- **Interactive compliance workflow** (edit areas, re-check compliance)

## Environment Variables

**Required:**
- `GOOGLE_API_KEY` - **For blueprint extraction** (Gemini 2.0 Flash is default vision LLM)
- `OPENAI_API_KEY` - For text-based LLM features (rule extraction, RAG chat)

**Optional:**
- `VISION_LLM_PROVIDER` - Vision LLM provider: `"gemini"` (default) or `"openai"` (GPT-4o)
- `QDRANT_URL` - Qdrant server URL (defaults to in-memory)
- `QDRANT_API_KEY` - Qdrant API key (if using hosted Qdrant)
- `PORT` - Server port (defaults to 8000, Railway sets this automatically)
- `HOST` - Server host (defaults to 0.0.0.0 for production)

## Troubleshooting

### Railway Deployment Issues

1. **Build fails**: Check that `pyproject.toml` and `uv.lock` are in `backend/` directory
2. **App crashes**: Check Railway logs, ensure `GOOGLE_API_KEY` and `OPENAI_API_KEY` are set
3. **Port issues**: Railway sets `$PORT` automatically, don't hardcode port 8000
4. **Blueprint extraction fails**: Verify `GOOGLE_API_KEY` is set (required for Gemini 2.0 Flash)

### Local Testing Issues

1. **Import errors**: Ensure you're in `backend/` directory when running commands
2. **Missing dependencies**: Run `uv sync` to install all dependencies
3. **API key errors**: Ensure `.env` file exists with `GOOGLE_API_KEY` and `OPENAI_API_KEY` set
4. **Blueprint extraction fails**: Check that `GOOGLE_API_KEY` is valid (Gemini 2.0 Flash requires this)

## Notes

- **First request**: Rule extraction and PDF indexing happen on first request (may take 30-60 seconds)
- **Blueprint extraction**: Uses Gemini 2.0 Flash by default (faster, better recall than GPT-4o per evaluation)
- **File uploads**: Supports PNG, JPG, and PDF files (multi-page PDFs are combined or can extract specific page)
- **Caching**: Embeddings and LLM responses are cached for performance
- **Static files**: All static files (plan.png, styles.css, overlays.json) are included in deployment
- **Data files**: Sample data (rooms.csv, doors.csv, PDFs) are included for demo
- **UI layout**: Blueprint Extraction moved to right panel with tab toggle (Q&A Chat ↔ Blueprint Extraction)

## Support

For issues or questions, check:
- `DEPLOYMENT_TESTING_PLAN.md` - **Focused testing plan for blueprint extraction features**
- `DEPLOYMENT_CHECKLIST.md` - Step-by-step deployment checklist
- `memory-bank/deployment.md` - Detailed deployment guide
- `backend/app/tests/TEST_RESULTS.md` - Test results and verification
- `README.md` - Project overview and setup

