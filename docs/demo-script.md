# Demo Script - Code-Aware Space Planning Copilot

**Duration:** 3.5 minutes  
**Context:** MVP is proof-of-concept Add-In for CAD software (AutoCAD/Revit)

---

## Pre-Demo Setup

1. **Open Railway deployment URL** (or `http://localhost:8000`)
2. **Verify demo data is loaded:**
   - Rooms: R101 (8.5 m² - violation), R102, R201, R301
   - Doors: D1 (750 mm), D2 (800 mm), D3 (700 mm), D4 (900 mm)
   - Building code PDFs indexed
   - Overlays loaded

---

## Demo Flow (3.5 minutes)

### Step 1: Context & Overview (15 seconds)

**Talking Points:**
- "This MVP demonstrates a CAD Add-In for building code compliance"
- "CSV files represent data exported from AutoCAD/Revit"
- "The web UI demonstrates functionality that would embed in CAD software"
- "In production, this would integrate directly into CAD software"

**Action:**
- Show the full frontend UI (plan viewer, issues list, chat panel)

---

### Step 2: Show Compliance Issues (45 seconds)

**Talking Points:**
- "The system automatically checks design elements against building code rules"
- "Rules come from two sources: seeded rules and LLM-extracted rules from PDFs"
- "We found 13 compliance issues in this design"

**Action:**
1. Point to the **Compliance Issues** panel (bottom)
2. Show the list of violations:
   - **Room violation:** R101 (North Bedroom) - 8.5 m² < 9.5 m² minimum
   - **Door violations:** Multiple doors fail width requirements

**Expected Issues (from test results):**

**Room Violations (1):**
- **R101 (North Bedroom):** Area 8.50 m², but minimum required is 9.50 m²
  - Rule: R001 (Minimum bedroom area)
  - Code Ref: NBC Section 8.2.1 - Minimum habitable room area

**Door Violations (12):**
- **D1 (750 mm):** 4 violations
  - Violates 800 mm (Minimum accessible door width) - Rule D001
  - Violates 1200 mm (Minimum width for inner court passageway) - Rule R003
  - Violates 800 mm (Minimum height of sleeping room window) - Rule D102 ⚠️ *Note: This rule seems incorrectly applied*
  - Violates 900 mm (Minimum width of exit access from sleeping rooms) - Rule D104

- **D2 (800 mm):** 2 violations
  - Violates 1200 mm (Minimum width for inner court passageway) - Rule R003
  - Violates 900 mm (Minimum width of exit access from sleeping rooms) - Rule D104

- **D3 (700 mm):** 5 violations
  - Violates 800 mm (Minimum accessible door width) - Rule D001
  - Violates 750 mm (Minimum width for projection room door) - Rule D100
  - Violates 1200 mm (Minimum width for inner court passageway) - Rule R003
  - Violates 800 mm (Minimum height of sleeping room window) - Rule D102 ⚠️ *Note: This rule seems incorrectly applied*
  - Violates 900 mm (Minimum width of exit access from sleeping rooms) - Rule D104

- **D4 (900 mm):** 1 violation
  - Violates 1200 mm (Minimum width for inner court passageway) - Rule R003

**Note:** Some extracted rules may be incorrectly applied (e.g., window height rules applied to doors). This demonstrates that LLM extraction needs refinement, but the core violations (R101 area, D1/D3 accessible door width) are correct.

---

### Step 3: Visual Highlighting (30 seconds)

**Talking Points:**
- "Clicking on an issue highlights the corresponding element on the floor plan"
- "This helps architects quickly identify problem areas"

**Action:**
1. Click on **R101 violation** (North Bedroom area violation)
2. Show the **red highlight** appearing on the floor plan overlay
3. Click on **D1 violation** (door width violation)
4. Show the **red highlight** moving to the door overlay

**Expected Behavior:**
- Red border and pulsing animation on selected overlay
- Highlight persists until another issue is selected
- Overlay coordinates match the plan image

---

### Step 4: Conversational Chat with Blueprint Context (60 seconds)

**Talking Points:**
- "The system supports conversational chat with context awareness"
- "It maintains conversation history and integrates with extracted blueprint data"
- "You can ask follow-up questions and reference specific rooms from uploaded blueprints"

**Action 1: Ask about minimum bedroom area (15 seconds)**
- Type: **"What is the minimum bedroom area?"**
- Click Send
- Wait for response
- **Note:** System generates a `conversation_id` automatically (shown in response)

**Expected Response:**
- Answer mentions minimum bedroom area requirements
- May reference 9.5 m² (from seeded rules) or values from PDFs
- Includes citations with page numbers
- Response includes `conversation_id` for maintaining context

**Action 2: Follow-up question (15 seconds)**
- Type: **"What about bathrooms?"**
- Click Send
- Wait for response

**Expected Response:**
- Answer understands this is a follow-up about bathroom requirements
- Uses conversation history to provide context-aware response
- May reference previous bedroom question implicitly

**Action 3: Ask about uploaded PDF (15 seconds)**
- Switch to "📚 Upload Building Codes" tab
- Upload a building code PDF (e.g., `B344_AccessibilityLaw_2.pdf`)
- Wait for "✅ Successfully indexed" message
- Switch back to "💬 Q&A Chat" tab
- Type: **"Tell me about the minimum ramp width based on the B344_AccessibilityLaw_2.pdf"**
- Click Send
- Wait for response

**Expected Response:**
- Answer retrieves information from the uploaded PDF
- Citations show the uploaded PDF filename (e.g., `B344_AccessibilityLaw_2`)
- Demonstrates that uploaded PDFs are immediately available for RAG queries

**Action 4: Ask about blueprint context (15 seconds)**
- If you have extracted rooms from a blueprint:
  - Type: **"Is bedroom 1 compliant with minimum area requirements?"**
  - Click Send
  - Wait for response

**Expected Response:**
- Answer references the specific room from extracted blueprint data
- Mentions actual room area and compares to requirements
- Demonstrates blueprint context integration

---

### Step 5: PDF Upload for Building Codes (30 seconds)

**Talking Points:**
- "Users can upload their own building code PDFs"
- "Uploaded PDFs are immediately indexed and available for both chat queries and compliance checking"
- "This enables multi-jurisdiction support and custom code sets"

**Action:**
1. Switch to "📚 Upload Building Codes" tab
2. Show the upload interface
3. Upload a sample PDF (if not already done)
4. Show success message with chunk count
5. Show uploaded codes list (if any previous uploads)
6. Explain that uploaded PDFs are:
   - Available for RAG queries in chat
   - Included in rule extraction for compliance checking
   - Saved persistently for future use

**Expected Behavior:**
- Upload shows "Uploading and indexing PDF..." status
- Success message: "✅ Successfully indexed 'filename.pdf' (X chunks)"
- Uploaded PDF appears in list with filename, chunk count, and timestamp
- PDF is immediately searchable in chat queries
- PDF is included in compliance rule extraction

---

### Step 6: Closing (20 seconds)

**Talking Points:**
- "This MVP demonstrates core functionality for CAD Add-In integration"
- "Key features: Automated compliance checking, conversational chat with blueprint context, PDF upload for custom codes"
- "Future enhancements: Direct CAD integration, user-provided API keys, advanced features"

**Action:**
- Show the full UI one more time
- Highlight the key features:
  1. Automated compliance checking
  2. Visual issue highlighting
  3. Conversational RAG-powered code Q&A with blueprint context
  4. PDF upload for custom building codes

---

## Expected Test Results Summary

### Compliance Check Results

**Total Issues:** 13

**Room Violations:** 1
- R101: 8.5 m² < 9.5 m² minimum (✅ Correct - this is the main demo violation)

**Door Violations:** 12
- D1: 4 violations (750 mm fails multiple width requirements)
- D2: 2 violations (800 mm fails exit access requirements)
- D3: 5 violations (700 mm fails multiple width requirements)
- D4: 1 violation (900 mm fails inner court passageway requirement)

**Note:** Some violations may be from incorrectly extracted rules (e.g., window height rules applied to doors). The core violations (R101 area, D1/D3 accessible door width) are correct and should be emphasized in the demo.

### Chat Endpoint Results

**Test 1: "What is the minimum bedroom area?"**
- Response: May vary - system may say it doesn't have explicit information, but should provide relevant context
- Citations: 3-4 citations from building code PDFs
- Page numbers: Explicitly shown (e.g., "Page: 96 (PDF page)")

**Test 2: "Why is room R101 non-compliant?"**
- Response: Explains R101 has area 8.5 m², below 9.5 m² minimum
- May also mention exit access requirements from PDFs
- Citations: 3-5 citations with page numbers and sections

**Test 3: "What are the door width requirements?"**
- Response: Lists door width requirements (710 mm minimum, 800 mm for accessible, etc.)
- Citations: 3-5 citations from building code PDFs
- Page numbers: Explicitly shown with section numbers when available

---

## Demo Tips

1. **Emphasize Add-In Architecture:**
   - Always mention that CSV = CAD data proxy, UI = CAD UI proxy
   - Explain this would integrate directly into AutoCAD/Revit

2. **Focus on Core Violations:**
   - Highlight R101 (room area) - this is the clearest violation
   - Highlight D1/D3 (accessible door width) - these are correct violations
   - Note that some extracted rules may need refinement (but this shows the system is working)

3. **Show RAG Capabilities:**
   - Demonstrate that answers come from building code PDFs
   - Point out citations with page numbers
   - Explain this saves architects from reading entire code documents

4. **Timing:**
   - Keep each step within allocated time
   - If chat responses are slow, have backup screenshots ready
   - Practice the flow to ensure smooth transitions

---

## Backup Plan

If live demo fails:
1. Use screenshots from `docs/screenshots/` directory
2. Show pre-recorded video (if available)
3. Walk through the architecture diagram instead
4. Focus on explaining the system design and capabilities

---

## Post-Demo Q&A Preparation

**Common Questions:**
- **"How accurate is the rule extraction?"** → Explain that it's a proof-of-concept, some rules need refinement, but core violations are correct
- **"Can it handle multiple jurisdictions?"** → Yes, users can upload PDFs from different jurisdictions via the Upload Building Codes tab. Uploaded PDFs are immediately available for both chat queries and compliance checking
- **"How does conversational chat work?"** → System maintains conversation history per conversation_id, enabling follow-up questions. Blueprint context integration allows referencing specific extracted rooms
- **"What about BIM integration?"** → This is post-MVP; CSV is a proxy for CAD data export
- **"How does RAG work?"** → BM25 retrieval (validated best for building codes), then LLM generates answers with citations. Uploaded PDFs are indexed and searchable immediately

---

## Files Referenced

- Demo data: `backend/app/data/rooms.csv`, `backend/app/data/doors.csv`
- Building codes: `backend/app/data/National-Building-Code.pdf`, `backend/app/data/RA9514-RIRR-rev-2019-compressed.pdf`
- Overlays: `backend/app/static/overlays.json`
- Plan image: `backend/app/static/plan.png`
- Verification report: `docs/demo-data-verification.md`

