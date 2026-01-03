# Deployment Guide

Reference document for deploying the Code-Aware Space Planning Copilot MVP for assessment and public access.

## Deployment Options

### Option 1: Railway.app (Recommended for Bootcamp Demo)

**Pros:**
- Free tier available
- Auto-detects Python/FastAPI
- Easy GitHub integration
- ~5 minute setup
- Provides public URL automatically

**Steps:**
1. Push code to GitHub
2. Go to [Railway.app](https://railway.app) and sign in
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variable: `OPENAI_API_KEY` (in Railway dashboard → Variables)
6. Railway auto-detects Python and deploys
7. App live at `https://your-app.railway.app`

**Required Files:**
- `backend/railway.json` (optional config)
- `backend/.env.example` (documentation)

### Option 2: Docker (Portable)

**Pros:**
- Works anywhere Docker runs
- Consistent environment
- Easy local testing
- Can deploy to any container platform

**Steps:**
1. Build image: `docker build -t space-code-copilot backend/`
2. Run: `docker run -p 8000:8000 -e OPENAI_API_KEY=your_key space-code-copilot`
3. Or deploy to: Railway, Render, Fly.io, AWS ECS, etc.

**Required Files:**
- `backend/Dockerfile`
- `backend/.dockerignore`

### Option 3: Local Demo (For Assessors)

**Pros:**
- No cloud setup needed
- Full control
- Good for development/testing

**Steps:**
1. Clone repo
2. `cd backend && uv sync`
3. Copy `.env.example` to `.env`, add `OPENAI_API_KEY`
4. `uv run uvicorn app.main:app --reload`
5. Open `http://localhost:8000`

## Pre-Deployment Checklist

### Required Files

- [ ] `backend/.env.example` - Environment variable template
- [ ] `backend/Dockerfile` - Docker configuration (if using Docker)
- [ ] `backend/.dockerignore` - Docker ignore patterns
- [ ] `backend/railway.json` - Railway config (optional)
- [ ] `DEPLOYMENT.md` - Deployment instructions for assessors (in repo root)
- [ ] `README.md` - Updated with deployment section

### Sample Data

- [ ] `backend/app/data/rooms.csv` - Sample room schedule
- [ ] `backend/app/data/doors.csv` - Sample door schedule
- [ ] `backend/app/data/code_sample.pdf` - Sample building code PDF (optional for MVP)
- [ ] `backend/app/data/overlays.json` - Plan overlay data (optional)
- [ ] `backend/app/static/plan.png` - Floor plan image
- [ ] `backend/app/static/styles.css` - Frontend styles

### Frontend

- [ ] `backend/app/templates/index.html` - Frontend UI (can be minimal for MVP)
- [ ] Frontend displays issues from `/api/issues`
- [ ] Basic styling in `styles.css`

### Environment Variables

**Required:**
- `OPENAI_API_KEY` - For LLM features (rule extraction, RAG chat)

**Optional:**
- `QDRANT_URL` - Qdrant server URL (defaults to in-memory)
- `QDRANT_API_KEY` - Qdrant API key (if using hosted Qdrant)
- `PORT` - Server port (defaults to 8000)
- `HOST` - Server host (defaults to 0.0.0.0 for production)

### Testing

Before deploying, verify locally:
- [ ] `GET /health` → `{"status": "ok"}`
- [ ] `GET /api/issues` → Returns list of compliance issues
- [ ] `GET /` → Frontend UI loads
- [ ] Frontend displays issues from API
- [ ] All dependencies install correctly (`uv sync`)

## Deployment Files to Create

### 1. `backend/.env.example`

```bash
# LLM Provider (required for LLM features)
OPENAI_API_KEY=your_key_here

# Optional: Qdrant (defaults to in-memory for MVP)
# QDRANT_URL=http://localhost:6333
# QDRANT_API_KEY=your_key_here

# Optional: App config
# PORT=8000
# HOST=0.0.0.0
```

### 2. `backend/railway.json`

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 3. `backend/Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY app/ ./app/

# Expose port
EXPOSE 8000

# Run the application
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 4. `backend/.dockerignore`

```
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
*.egg-info/
dist/
build/
.git/
.gitignore
.env
cache/
*.db
```

### 5. `DEPLOYMENT.md` (in repo root)

```markdown
# Deployment Guide for Assessors

## Quick Start (Local)

1. Clone: `git clone <repo-url>`
2. Setup: `cd backend && uv sync`
3. Configure: Copy `.env.example` to `.env`, add `OPENAI_API_KEY`
4. Run: `uv run uvicorn app.main:app --reload`
5. Open: http://localhost:8000

## What to Test

- ✅ `GET /health` → `{"status": "ok"}`
- ✅ `GET /api/issues` → List of compliance issues
- ✅ `GET /` → Frontend UI showing issues
- ✅ Frontend displays issues from API

## MVP Features

- CSV-based room/door loading
- Compliance checking against seeded rules
- Issue reporting via API
- (Optional) LLM-based rule extraction from PDFs
```

## Minimal Frontend (If Missing)

If `backend/app/templates/index.html` is empty, add minimal version:

```html
<!DOCTYPE html>
<html>
<head>
    <title>Code-Aware Space Planning Copilot</title>
    <link rel="stylesheet" href="/static/styles.css">
</head>
<body>
    <h1>Code-Aware Space Planning Copilot</h1>
    
    <div id="issues">
        <h2>Compliance Issues</h2>
        <div id="issues-list">Loading...</div>
    </div>
    
    <script>
        // Fetch and display issues
        fetch('/api/issues')
            .then(r => r.json())
            .then(issues => {
                const list = document.getElementById('issues-list');
                if (issues.length === 0) {
                    list.innerHTML = '<p>No compliance issues found.</p>';
                } else {
                    list.innerHTML = issues.map(issue => 
                        `<div class="issue">
                            <strong>${issue.element_type} ${issue.element_id}</strong>: 
                            ${issue.message}
                            <small>(${issue.code_ref})</small>
                        </div>`
                    ).join('');
                }
            })
            .catch(err => {
                document.getElementById('issues-list').innerHTML = 
                    `<p>Error: ${err.message}</p>`;
            });
    </script>
</body>
</html>
```

## README Updates

Add deployment section to `README.md`:

```markdown
## Deployment

### Railway.app (Recommended)

1. Push your code to GitHub
2. Go to [Railway.app](https://railway.app) and sign in
3. Click "New Project" → "Deploy from GitHub repo"
4. Select your repository
5. Add environment variable: `OPENAI_API_KEY` (in Railway dashboard → Variables)
6. Railway will auto-detect Python and deploy
7. Your app will be live at `https://your-app.railway.app`

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
```

## Recommended Approach for Bootcamp Demo

1. **Deploy to Railway.app** (fastest, ~5 min setup)
   - Provides public URL immediately
   - Free tier sufficient for demo
   - Easy to share with assessors

2. **Share GitHub repo** (for code review)
   - Include `DEPLOYMENT.md` for local testing
   - Clear README with setup instructions

3. **Include assessment guide** (what to test)
   - Health endpoint
   - Issues API
   - Frontend UI
   - MVP features checklist

## Notes

- **Environment variables**: Never commit `.env` file, only `.env.example`
- **Dependencies**: Ensure `pyproject.toml` has all required packages
- **Port binding**: Use `0.0.0.0` for production (not `127.0.0.1`)
- **CORS**: Already configured in `main.py` for `*` origins (adjust for production)
- **Static files**: Ensure `app/static/` directory exists with required assets
- **Data files**: Include sample data in `app/data/` for demo

## Future Enhancements

- Add health check endpoint for monitoring
- Add logging configuration
- Add rate limiting for API endpoints
- Add authentication (if needed)
- Add persistent Qdrant storage (instead of in-memory)
- Add CI/CD pipeline (GitHub Actions)

