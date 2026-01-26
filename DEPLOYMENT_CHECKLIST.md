# Deployment Checklist

Use this checklist to deploy your app to Railway.app and get a public URL.

## Pre-Deployment

- [x] All end-to-end tests pass (`uv run python app/tests/test_e2e.py`)
- [x] Deployment files created:
  - [x] `backend/.env.example` - Environment variable template
  - [x] `backend/railway.json` - Railway configuration
  - [x] `backend/Dockerfile` - Docker configuration
  - [x] `backend/.dockerignore` - Docker ignore patterns
  - [x] `DEPLOYMENT.md` - Deployment guide
  - [x] `README.md` - Updated with deployment section

## Step 1: Prepare Code

- [x] Commit all changes:
  ```bash
  git add .
  git commit -m "Add deployment files and configuration"
  ```

- [x] Push to GitHub:
  ```bash
  git push origin main
  ```
  Note: Only in origin feature/multimodal (branch)

## Step 2: Deploy to Railway.app

1. [x] Go to [Railway.app](https://railway.app) and sign in (GitHub OAuth)

2. [x] Click "New Project" → "Deploy from GitHub repo"

3. [x] Select your repository (`space-code-copilot`)

4. [x] Railway will auto-detect Python and start building
   - Wait for build to complete (2-5 minutes)

5. [x] Configure environment variables:
   - Go to your project → Variables tab
   - Add required keys:
     - `GOOGLE_API_KEY` = `your_gemini_api_key` (for blueprint extraction - Gemini 2.0 Flash is default)
     - `OPENAI_API_KEY` = `your_openai_api_key` (for rule extraction and RAG chat)
   - Optional: `VISION_LLM_PROVIDER` = `"gemini"` (default) or `"openai"`
   - Railway will automatically restart the service

6. [x] Get your public URL:
   - Go to Settings → Domains
   - Railway provides a default domain: `https://your-app-name.railway.app`
   - Or generate a custom domain

## Step 3: Verify Deployment

Test your deployed app:

### Basic Endpoints

- [x] Health check: `https://your-app.railway.app/health`
  - Should return: `{"status": "ok"}`

- [x] Issues API: `https://your-app.railway.app/api/issues`
  - Should return JSON array of compliance issues

- [x] Chat API: `https://your-app.railway.app/api/chat`
  - Test with: `{"query": "What is the minimum bedroom area?"}`
  - Should return answer with citations

  Note: Return: {"detail":"Method Not Allowed"}

### Blueprint Extraction Endpoints

- [ ] `POST /api/blueprint/extract/` (file upload)
  - Upload a PNG/JPG/PDF blueprint file
  - Should return `BlueprintExtractionResult` with extracted rooms
  - Test with: `curl -X POST -F "file=@blueprint.pdf" -F "scale=1.0" https://your-app.railway.app/api/blueprint/extract/`

- [ ] `POST /api/blueprint/extract-and-check/` (file upload)
  - Upload blueprint, extract rooms, check compliance
  - Should return extraction + issues + summary
  - Test with: `curl -X POST -F "file=@blueprint.pdf" https://your-app.railway.app/api/blueprint/extract-and-check/`

- [ ] `POST /api/blueprint/check-compliance/` (JSON body)
  - Send edited room data for re-checking compliance
  - Test with: `curl -X POST -H "Content-Type: application/json" -d '[{"id":"R1","name":"Bedroom 1","type":"bedroom","level":1,"area_m2":8.5}]' https://your-app.railway.app/api/blueprint/check-compliance/`

### Frontend UI

- [x] Frontend: `https://your-app.railway.app/`
  - Should load the UI with plan viewer (left), issues list (bottom), and right panel with tabs

- [ ] **Q&A Chat tab** (default):
  - Chat panel works for building code questions
  - Citations display correctly

- [ ] **Blueprint Extraction tab**:
  - Tab toggle works (switch between Q&A Chat and Blueprint Extraction)
  - Plan viewer shows empty placeholder initially
  - File upload works (drag-and-drop or click to upload)
  - Uploaded blueprint displays in plan viewer
  - "Extract Rooms" button extracts and displays room table
  - Area column is editable (can type new values)
  - "Check Compliance" button appears and works
  - Compliance column appears after first check
  - Per-room check button (✓) works for individual rooms
  - Tooltips show compliance issues (hover over compliance status)
  - Tooltips appear above table header (not cut off)

## Step 4: Share with Mentors/Cohorts

- [ ] Share the public URL: `https://your-app.railway.app`
- [ ] Share GitHub repo for code review
- [ ] Mention that first request may take 30-60 seconds (rule extraction + PDF indexing)
- [ ] Highlight new features:
  - Blueprint extraction from images (PNG/JPG/PDF)
  - Interactive compliance checking (edit areas, re-check)
  - Tab-based UI (Q&A Chat ↔ Blueprint Extraction)

## Troubleshooting

### Build Fails
- Check Railway logs for errors
- Ensure `pyproject.toml` and `uv.lock` are in `backend/` directory
- Verify Python version (3.11+)

### App Crashes
- Check Railway logs
- Verify `GOOGLE_API_KEY` and `OPENAI_API_KEY` are set correctly
- Check that all required files are in the repo
- Verify blueprint extraction endpoints are accessible (check router mounting in `app/main.py`)

### Port Issues
- Railway sets `$PORT` automatically
- Don't hardcode port 8000 in code
- The `railway.json` uses `$PORT` variable

### First Request Slow
- This is normal! First request triggers:
  - Rule extraction from PDFs (30-60 seconds)
  - PDF indexing for vector store (30-60 seconds)
- Subsequent requests are fast (cached)

## Alternative: Local Testing

If you prefer to test locally first:

```bash
cd backend
uv sync
cp .env.example .env
# Edit .env and add:
#   GOOGLE_API_KEY=your_gemini_key
#   OPENAI_API_KEY=your_openai_key
uv run uvicorn app.main:app --reload
```

Then test at: `http://localhost:8000`

## Next Steps After Deployment

1. ✅ Share public URL with mentors/cohorts
2. ✅ Prepare demo script (see `memory-bank/presentation.md`)
3. ✅ Practice demo flow (7 minutes)
4. ✅ Prepare for Q&A

## Notes

- **Free Tier**: Railway free tier is sufficient for demo
- **Auto-shutdown**: Railway may sleep inactive apps (free tier)
- **Environment Variables**: Never commit `.env` file, only `.env.example`
- **Static Files**: All static files are included in deployment
- **Data Files**: Sample data (CSV, PDFs) are included for demo
- **Blueprint Extraction**: Uses Gemini 2.0 Flash by default (requires `GOOGLE_API_KEY`)
- **File Upload Limits**: Railway may have file size limits (check Railway docs for current limits)
- **Multi-page PDFs**: Supported - can extract all pages combined or specific page via `page_index` parameter

