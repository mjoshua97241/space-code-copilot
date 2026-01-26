# Deployment Testing Plan - Feature/Multimodal Branch

Focused testing plan for blueprint extraction features in `feature/multimodal` branch.

## Pre-Deployment Verification

### Code Readiness
- [ ] All blueprint extraction endpoints are implemented and tested locally
- [ ] Frontend UI changes are complete (tabs, editable areas, compliance re-check)
- [ ] Environment variables documented in `.env.example`
- [ ] No hardcoded API keys or secrets in code
- [ ] Blueprint router is mounted in `app/main.py`

### Dependencies
- [ ] `pyproject.toml` includes all required packages:
  - `pillow` (image processing)
  - `pymupdf` (PDF handling)
  - `langchain-google-genai` (Gemini 2.0 Flash)
  - `langchain-openai` (GPT-4o, optional)
- [ ] `uv.lock` is up to date

## Environment Variables Setup

### Required for Railway
- [ ] `GOOGLE_API_KEY` - **Required** for blueprint extraction (Gemini 2.0 Flash)
- [ ] `OPENAI_API_KEY` - Required for rule extraction and RAG chat

### Optional
- [ ] `VISION_LLM_PROVIDER` - Set to `"gemini"` (default) or `"openai"` if using GPT-4o

## API Endpoint Testing

### 1. Health Check
```bash
curl https://your-app.railway.app/health
```
**Expected**: `{"status": "ok"}`

### 2. Blueprint Extraction - Basic
```bash
curl -X POST \
  -F "file=@backend/app/data/floor-plans/example_plan_01a.pdf" \
  -F "scale=1.0" \
  https://your-app.railway.app/api/blueprint/extract/
```
**Expected**:
- Status: 200 OK
- Response: `BlueprintExtractionResult` with:
  - `rooms`: Array of extracted Room objects
  - `confidence`: Confidence scores
  - `scale_used`: 1.0
  - `extraction_metadata`: Model info

**Verify**:
- [ ] Rooms are extracted (non-empty array)
- [ ] Room objects have: id, name, type, level, area_m2
- [ ] Confidence scores are between 0.0 and 1.0
- [ ] No errors in response

### 3. Blueprint Extraction - Multi-page PDF
```bash
curl -X POST \
  -F "file=@backend/app/data/floor-plans/example_plan_01a.pdf" \
  -F "scale=1.0" \
  -F "page_index=0" \
  https://your-app.railway.app/api/blueprint/extract/
```
**Expected**: Extracts from specific page (page 0)

**Verify**:
- [ ] Works with `page_index=0`
- [ ] Works with `page_index=1` (if PDF has multiple pages)
- [ ] Works without `page_index` (combines all pages)

### 4. Blueprint Extraction - Different File Types
Test with:
- [ ] PNG file (`.png`)
- [ ] JPG file (`.jpg` or `.jpeg`)
- [ ] PDF file (`.pdf`)

**Verify**:
- [ ] All file types are accepted
- [ ] Invalid file types are rejected (400 error)

### 5. Extract and Check Compliance
```bash
curl -X POST \
  -F "file=@backend/app/data/floor-plans/example_plan_01a.pdf" \
  -F "scale=1.0" \
  https://your-app.railway.app/api/blueprint/extract-and-check/
```
**Expected**:
- Status: 200 OK
- Response: Dictionary with:
  - `extraction`: BlueprintExtractionResult
  - `issues`: List[Issue] (compliance violations)
  - `summary`: Summary statistics

**Verify**:
- [ ] Extraction succeeds
- [ ] Compliance issues are found (if rooms violate rules)
- [ ] Summary statistics are correct
- [ ] Issues reference correct room IDs

### 6. Check Compliance Only (Re-check with Edited Data)
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '[{"id":"R1","name":"Bedroom 1","type":"bedroom","level":1,"area_m2":8.5}]' \
  https://your-app.railway.app/api/blueprint/check-compliance/
```
**Expected**:
- Status: 200 OK
- Response: Dictionary with:
  - `issues`: List[Issue] (violations for edited room)
  - `summary`: Summary statistics

**Verify**:
- [ ] Accepts JSON array of Room objects
- [ ] Returns compliance issues for edited room
- [ ] Summary reflects correct counts

## Frontend UI Testing

### 1. Basic UI Load
- [ ] Navigate to `https://your-app.railway.app/`
- [ ] Page loads without errors
- [ ] Layout displays correctly:
  - Left panel: Plan viewer (empty placeholder initially)
  - Right panel: Tab interface (Q&A Chat active by default)

### 2. Tab Toggle
- [ ] Click "💬 Q&A Chat" tab → Chat panel visible
- [ ] Click "🔍 Blueprint Extraction" tab → Extraction panel visible
- [ ] Only one tab content is visible at a time
- [ ] Active tab is highlighted
- [ ] Tab switching is smooth (no layout shifts)

### 3. Blueprint Extraction Workflow

#### Step 1: Upload Blueprint
- [ ] Click "🔍 Blueprint Extraction" tab
- [ ] Click file upload area or drag-and-drop a PDF/PNG/JPG
- [ ] File is accepted (no error messages)
- [ ] Plan viewer displays uploaded blueprint image
- [ ] Empty placeholder is replaced with actual blueprint

#### Step 2: Extract Rooms
- [ ] Click "Extract Rooms" button
- [ ] Loading indicator appears
- [ ] Room table appears with extracted rooms
- [ ] Table columns: ID, Name, Area (editable), Compliance
- [ ] Type and Level columns are **not** visible (removed from UI)
- [ ] Compliance column is **hidden** initially

#### Step 3: Edit Area Values
- [ ] Click on an area value in the table
- [ ] Input field appears (replaces static text)
- [ ] Type a new value (e.g., change 14.0 to 8.5)
- [ ] Press Enter or click outside → Value is saved
- [ ] Edited value persists in the table

#### Step 4: Check Compliance
- [ ] Click "Check Compliance" button
- [ ] Compliance column **appears** (was hidden before)
- [ ] Compliance status shows for each room:
  - ✅ Green checkmark if compliant
  - ⚠️ Warning icon if non-compliant
- [ ] Hover over compliance status → Tooltip appears
- [ ] Tooltip shows compliance issues (not cut off by table header)
- [ ] Tooltip is wide enough to read (500px width)

#### Step 5: Per-Room Compliance Check
- [ ] Click the checkmark button (✓) next to a specific room
- [ ] Only that room's compliance is re-checked
- [ ] Compliance status updates for that room only
- [ ] Other rooms' statuses remain unchanged

### 4. Error Handling
- [ ] Upload invalid file type → Error message displayed
- [ ] Upload corrupted PDF → Error message displayed
- [ ] Extraction fails → Error message displayed (not crash)
- [ ] Network error → User-friendly error message

### 5. Q&A Chat Tab
- [ ] Switch to "Q&A Chat" tab
- [ ] Chat panel is fully visible
- [ ] Can type questions and get answers
- [ ] Citations display correctly
- [ ] Switching back to Blueprint Extraction preserves state

## Edge Cases & Stress Testing

### File Size Limits
- [ ] Test with small PDF (< 1MB)
- [ ] Test with medium PDF (1-5MB)
- [ ] Test with large PDF (> 5MB) - may hit Railway limits

### Multi-page PDFs
- [ ] Test with single-page PDF
- [ ] Test with multi-page PDF (all pages combined)
- [ ] Test with multi-page PDF (specific page via `page_index`)

### Invalid Inputs
- [ ] Upload non-image file (e.g., `.txt`)
- [ ] Upload corrupted image
- [ ] Send invalid JSON to `/check-compliance/`
- [ ] Send empty room list to `/check-compliance/`

### API Rate Limiting
- [ ] Make multiple extraction requests in quick succession
- [ ] Verify no rate limiting errors (if applicable)
- [ ] Check Railway logs for any throttling

## Performance Testing

### Response Times
- [ ] First extraction: < 30 seconds (acceptable for VLM)
- [ ] Subsequent extractions: < 20 seconds (caching may help)
- [ ] Compliance check: < 2 seconds (should be fast)

### Concurrent Requests
- [ ] Test multiple users uploading blueprints simultaneously
- [ ] Verify no crashes or deadlocks

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Edge (Chromium)
- [ ] Firefox
- [ ] Safari (if available)

**Verify**:
- [ ] File upload works (drag-and-drop and click)
- [ ] Tab switching works
- [ ] Editable area inputs work
- [ ] Tooltips display correctly
- [ ] No console errors

## Mobile Responsiveness (Optional)

- [ ] Test on mobile device or browser dev tools
- [ ] Layout adapts to smaller screens
- [ ] File upload still works
- [ ] Tables are scrollable

## Post-Deployment Verification

### Railway Logs
- [ ] Check Railway logs for errors
- [ ] Verify no import errors
- [ ] Verify no API key errors
- [ ] Check for memory leaks (if running for extended time)

### Monitoring
- [ ] Monitor Railway metrics (CPU, memory, requests)
- [ ] Check for any unexpected spikes
- [ ] Verify app doesn't crash under load

## Rollback Plan

If deployment fails:
1. [ ] Check Railway logs for specific error
2. [ ] Verify environment variables are set correctly
3. [ ] Test locally with same environment variables
4. [ ] If needed, rollback to previous working commit
5. [ ] Document the issue for future reference

## Success Criteria

Deployment is successful if:
- ✅ All API endpoints return expected responses
- ✅ Frontend UI loads and all features work
- ✅ Blueprint extraction works for PNG/JPG/PDF
- ✅ Compliance checking works with extracted and edited data
- ✅ No critical errors in Railway logs
- ✅ App remains stable under normal usage

## Next Steps After Successful Deployment

1. [ ] Share public URL with team/mentors
2. [ ] Document any deployment-specific notes
3. [ ] Update `DEPLOYMENT.md` with any lessons learned
4. [ ] Monitor app for first 24 hours
5. [ ] Collect user feedback on blueprint extraction features
