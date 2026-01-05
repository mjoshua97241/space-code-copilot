# End-to-End Testing Checklist

Use this checklist to verify all features work together before deployment.

## Pre-Test Setup

- [ ] Environment variables set (`.env` file or exported):
  - `OPENAI_API_KEY` (required for chat, vector store, rule extraction)
- [ ] Required files exist:
  - `app/data/rooms.csv`
  - `app/data/doors.csv`
  - `app/data/National-Building-Code.pdf` (or `code_sample.pdf`)
  - `app/data/overlays.json`
  - `app/static/plan.png`
  - `app/static/styles.css`
  - `app/static/overlays.json`
- [ ] Dependencies installed: `uv sync`

## Automated Tests

Run the comprehensive test suite:

```bash
cd backend
uv run python app/tests/test_e2e.py
```

Expected: **All 16 tests pass (100% success rate)**

## Manual Testing Checklist

### 1. Health Check
- [ ] Visit `http://localhost:8000/health`
- [ ] Should return: `{"status": "ok"}`

### 2. Frontend
- [ ] Visit `http://localhost:8000/`
- [ ] Page loads without errors
- [ ] Plan image displays
- [ ] Issues list appears (may be empty initially)
- [ ] Chat panel visible

### 3. Static Files
- [ ] `http://localhost:8000/static/plan.png` - Image loads
- [ ] `http://localhost:8000/static/styles.css` - CSS loads
- [ ] `http://localhost:8000/static/overlays.json` - JSON loads

### 4. Issues Endpoint
- [ ] Visit `http://localhost:8000/api/issues`
- [ ] Returns JSON array of issues
- [ ] Each issue has: `element_id`, `element_type`, `rule_id`, `message`, `code_ref`
- [ ] Visit `http://localhost:8000/api/issues/summary`
- [ ] Returns summary with `total` count

### 5. Chat Endpoint
- [ ] Send POST request to `/api/chat`:
  ```json
  {
    "query": "What is the minimum bedroom area?"
  }
  ```
- [ ] Response includes:
  - `answer` (non-empty string)
  - `citations` (array with source, page, section)
- [ ] Citations include page type: "(PDF page)" or "(document page)"

### 6. Overlays & Highlighting
- [ ] Load frontend page
- [ ] Click an issue in the issues list
- [ ] Corresponding overlay highlights in red on plan image
- [ ] Overlay has pulsing animation

### 7. Rule Extraction
- [ ] First request to `/api/issues` triggers rule extraction
- [ ] Console shows extraction progress
- [ ] Rules extracted from PDFs
- [ ] Project context filtering applied (residential, single-story)

### 8. Compliance Checking
- [ ] Issues endpoint returns compliance violations
- [ ] Room issues appear (if any rooms violate rules)
- [ ] Door issues appear (if any doors violate rules)
- [ ] Issue messages are clear and actionable

## Integration Tests

### Test Flow 1: Full Compliance Check
1. [ ] Load design data (rooms.csv, doors.csv)
2. [ ] Extract rules from PDFs (with project context)
3. [ ] Check compliance
4. [ ] Verify issues returned match expected violations

### Test Flow 2: RAG Chat
1. [ ] Index PDFs (happens on first chat request)
2. [ ] Ask question about building code
3. [ ] Verify answer is relevant
4. [ ] Verify citations are accurate

### Test Flow 3: Frontend Integration
1. [ ] Load frontend page
2. [ ] Issues list populates automatically
3. [ ] Click issue → overlay highlights
4. [ ] Submit chat query → answer appears
5. [ ] Citations display correctly

## Performance Checks

- [ ] First rule extraction: < 60 seconds
- [ ] First PDF indexing: < 60 seconds
- [ ] Subsequent API calls: < 5 seconds
- [ ] Frontend page load: < 2 seconds

## Error Handling

- [ ] Missing API key: Chat endpoint returns error (not crash)
- [ ] Missing PDF: Rule extraction fails gracefully
- [ ] Invalid CSV: Design loader handles errors
- [ ] Network errors: Frontend shows user-friendly messages

## Browser Compatibility

Test in multiple browsers:
- [ ] Chrome/Edge
- [ ] Firefox
- [ ] Safari (if available)

## Deployment Readiness

Before deploying, verify:
- [ ] All automated tests pass
- [ ] Manual tests completed
- [ ] No console errors in browser
- [ ] No terminal errors in backend
- [ ] Environment variables documented
- [ ] Deployment guide reviewed (`memory-bank/deployment.md`)

## Known Issues

None currently - all tests passing ✅

## Test Results

Last run: See `TEST_RESULTS.md` for detailed results.

