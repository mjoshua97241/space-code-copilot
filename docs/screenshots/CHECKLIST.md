# Screenshot Capture Checklist

Use this checklist while capturing screenshots for the presentation.

## Preparation

- [ ] Railway.app is deployed and accessible (or local server running at `http://localhost:8000`)
- [ ] Demo data is correct:
  - [ ] `backend/app/data/rooms.csv` has R101 with area 8.5 m² (violation)
  - [ ] `backend/app/data/doors.csv` has door violations
  - [ ] `backend/app/static/overlays.json` has room and door overlays
- [ ] Browser is ready (Chrome/Firefox/Edge, zoom at 100%)
- [ ] Screenshot tool is ready (Snipping Tool, Print Screen, or browser extension)

## Screenshots to Capture

### 1. Building Code PDF
- [ ] Open `backend/app/data/National-Building-Code.pdf` or `RA9514-RIRR-rev-2019-compressed.pdf`
- [ ] Navigate to a page with room area or door width requirements
- [ ] Capture: `screenshot-building-code-pdf.png`
- [ ] **Verify:** Text is readable, shows code complexity

### 2. Frontend UI - Full View
- [ ] Open Railway URL or `http://localhost:8000`
- [ ] Wait for page to load completely
- [ ] Capture entire browser window: `screenshot-frontend-full.png`
- [ ] **Verify:** All three panels visible (plan, issues, chat)

### 3. Plan Viewer with Red Highlight
- [ ] On the frontend, click on a compliance issue from the list
- [ ] Wait for red highlight to appear on the plan
- [ ] Capture: `screenshot-plan-highlight.png`
- [ ] **Verify:** Red border/overlay is clearly visible on the plan

### 4. Compliance Issues List
- [ ] Scroll to focus on the bottom issues panel
- [ ] Ensure multiple issues are visible (room + door violations)
- [ ] Capture: `screenshot-issues-list.png`
- [ ] **Verify:** Issue messages are readable, severity badges visible

### 5. Chat Interface - Question
- [ ] Focus on the right chat panel
- [ ] Type a question: "What is the minimum bedroom area?"
- [ ] Capture before or just after submitting: `screenshot-chat-question.png`
- [ ] **Verify:** Question text is visible and clear

### 6. Chat Interface - Response with Citations
- [ ] Wait for RAG response to load
- [ ] Scroll to show the full answer and citations
- [ ] Capture: `screenshot-chat-response.png`
- [ ] **Verify:** Answer text is visible, citations show page numbers

### 7. Railway Dashboard (Optional)
- [ ] Log into Railway.app
- [ ] Navigate to your project dashboard
- [ ] Show deployment status
- [ ] Capture: `screenshot-railway-dashboard.png`
- [ ] **Verify:** Service status is visible (deployed/running)

## Post-Capture Verification

- [ ] All 7 (or 6 if skipping Railway) screenshots saved in `docs/screenshots/`
- [ ] File names match exactly: `screenshot-*.png`
- [ ] Images are clear and readable
- [ ] Text in images is legible (not blurry)
- [ ] Screenshots show the intended features clearly

## Notes

- **Railway URL:** Use your actual Railway deployment URL (e.g., `https://your-app.railway.app`)
- **Local alternative:** If Railway is not accessible, use `http://localhost:8000` but note this in presentation
- **Browser:** Use a clean browser window (minimal extensions, no clutter)
- **Window size:** Use full-screen or large window (1920x1080 or higher)

