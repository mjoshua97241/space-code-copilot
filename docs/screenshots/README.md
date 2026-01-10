# Screenshots Guide

This directory contains screenshots for the presentation demo.

## Required Screenshots

### 1. Building Code PDF
**File:** `screenshot-building-code-pdf.png`
**What to capture:**
- Open one of the building code PDFs (e.g., `backend/app/data/National-Building-Code.pdf` or `RA9514-RIRR-rev-2019-compressed.pdf`)
- Show a page with relevant building code text (room area requirements, door width requirements)
- Highlight the complexity/density of the document
- **Purpose:** Demonstrate the challenge of manually reading through dense code documents

### 2. Frontend UI - Full View
**File:** `screenshot-frontend-full.png`
**What to capture:**
- Open the deployed Railway URL or local `http://localhost:8000`
- Capture the entire frontend UI showing:
  - Left: Floor plan image with overlays
  - Bottom: Compliance issues list
  - Right: Chat panel
- **Purpose:** Show the complete application interface

### 3. Plan Viewer with Highlights
**File:** `screenshot-plan-highlight.png`
**What to capture:**
- Same as above, but after clicking on a compliance issue
- Show the red highlight overlay on the floor plan
- Ensure the issue is clearly visible (red border, pulsing animation)
- **Purpose:** Demonstrate visual issue highlighting feature

### 4. Compliance Issues List
**File:** `screenshot-issues-list.png`
**What to capture:**
- Focus on the bottom panel showing the compliance issues list
- Show multiple issues (room area violation, door width violations)
- Include severity badges if visible
- **Purpose:** Show automated compliance checking results

### 5. Chat Interface - Question
**File:** `screenshot-chat-question.png`
**What to capture:**
- Focus on the right chat panel
- Show a user question typed in (e.g., "What is the minimum bedroom area?")
- Before submitting, or just after submitting
- **Purpose:** Show the chat interface for building code Q&A

### 6. Chat Interface - Response with Citations
**File:** `screenshot-chat-response.png`
**What to capture:**
- Same chat panel, but showing the RAG response
- Include the answer text
- Show citations with page numbers (e.g., "Source: RA9514-RIRR-rev-2019-compressed.pdf, Page: 96 (PDF page)")
- **Purpose:** Demonstrate RAG-powered answers with citations

### 7. Railway Dashboard (Optional)
**File:** `screenshot-railway-dashboard.png`
**What to capture:**
- Railway.app deployment dashboard
- Show the service status (deployed, running)
- Show deployment logs or metrics if available
- **Purpose:** Show deployment status and public availability

## Screenshot Specifications

- **Format:** PNG (preferred) or JPG
- **Resolution:** At least 1920x1080 (Full HD) or higher
- **Naming:** Use the exact filenames listed above
- **Quality:** Clear, readable text, good contrast

## How to Capture

### On Linux (WSL/Desktop):
- Use `gnome-screenshot` or `flameshot` for interactive screenshots
- Or use `Print Screen` key and save
- Browser: Use browser extensions or built-in screenshot tools

### On Windows:
- Use `Windows + Shift + S` for Snipping Tool
- Or `Print Screen` key
- Browser: Use browser developer tools (F12) → More tools → Capture screenshot

### On Mac:
- Use `Command + Shift + 4` for area selection
- Or `Command + Shift + 3` for full screen
- Browser: Use browser developer tools or extensions

## Browser Recommendations

- Use Chrome, Firefox, or Edge
- Ensure browser zoom is at 100% (not zoomed in/out)
- Use full-screen or large window for better quality
- Disable browser extensions that might clutter the UI

## Checklist

- [ ] Building code PDF screenshot
- [ ] Frontend UI full view
- [ ] Plan viewer with red highlight
- [ ] Compliance issues list
- [ ] Chat interface with question
- [ ] Chat interface with response and citations
- [ ] Railway dashboard (optional)

## Notes

- All screenshots should be taken from the **deployed Railway.app URL** if possible (for presentation authenticity)
- If Railway is not accessible, use local `http://localhost:8000` but note this in the presentation
- Ensure demo data is correct (R101 violation should be visible)
- Test the chat with actual questions before capturing

