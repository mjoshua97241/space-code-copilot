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

- [ ] Commit all changes:
  ```bash
  git add .
  git commit -m "Add deployment files and configuration"
  ```

- [ ] Push to GitHub:
  ```bash
  git push origin main
  ```

## Step 2: Deploy to Railway.app

1. [ ] Go to [Railway.app](https://railway.app) and sign in (GitHub OAuth)

2. [ ] Click "New Project" → "Deploy from GitHub repo"

3. [ ] Select your repository (`space-code-copilot`)

4. [ ] Railway will auto-detect Python and start building
   - Wait for build to complete (2-5 minutes)

5. [ ] Configure environment variables:
   - Go to your project → Variables tab
   - Add: `OPENAI_API_KEY` = `your_actual_openai_api_key`
   - Railway will automatically restart the service

6. [ ] Get your public URL:
   - Go to Settings → Domains
   - Railway provides a default domain: `https://your-app-name.railway.app`
   - Or generate a custom domain

## Step 3: Verify Deployment

Test your deployed app:

- [ ] Health check: `https://your-app.railway.app/health`
  - Should return: `{"status": "ok"}`

- [ ] Frontend: `https://your-app.railway.app/`
  - Should load the UI with plan viewer, issues list, and chat

- [ ] Issues API: `https://your-app.railway.app/api/issues`
  - Should return JSON array of compliance issues

- [ ] Chat API: `https://your-app.railway.app/api/chat`
  - Test with: `{"query": "What is the minimum bedroom area?"}`
  - Should return answer with citations

## Step 4: Share with Mentors/Cohorts

- [ ] Share the public URL: `https://your-app.railway.app`
- [ ] Share GitHub repo for code review
- [ ] Mention that first request may take 30-60 seconds (rule extraction + PDF indexing)

## Troubleshooting

### Build Fails
- Check Railway logs for errors
- Ensure `pyproject.toml` and `uv.lock` are in `backend/` directory
- Verify Python version (3.11+)

### App Crashes
- Check Railway logs
- Verify `OPENAI_API_KEY` is set correctly
- Check that all required files are in the repo

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
# Edit .env and add OPENAI_API_KEY
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

