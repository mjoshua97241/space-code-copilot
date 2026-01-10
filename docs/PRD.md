# PRD – Code-Aware Space Planning Copilot

## 1. Overview

AI-assisted web app that helps architects and designers check early space planning (rooms, doors, corridors) against building codes and internal standards.

- **Form factor:** Single-page web UI served directly by FastAPI
- **Users:** Architects, designers, technical coordinators
- **Phase:** Early/mid design, before detailed BIM / spec submittals
- **MVP scope:** One sample project (single floor), small set of code rules, single-user
- **Frontend tech:** Plain HTML/CSS + minimal inline browser JavaScript, **no Node/npm, no React**
- **Deployment:** Railway.app (or Docker/local)
- **Architecture Context:** MVP is proof-of-concept for CAD Add-In integration (AutoCAD/Revit). CSV files are proxy for CAD data export, standalone web UI is proxy for CAD software UI.

---

## 2. Problem

### 2.1 Current pain

- Checking **room area**, **door clear width**, and **corridor width** against building code and internal standards is manual.
- Typical workflow:
  - Export schedules from CAD (rooms, doors).
  - Manually look up requirements in code PDFs or internal guideline PDFs.
  - Compare values in Excel, CAD, or on paper.
- Problems:
  - Time-consuming, repetitive.
  - Easy to miss violations.
  - Code is dense and hard to navigate during design exploration.
  - Feedback arrives late (code checker or consultant), causing rework.

### 2.2 Why now

- LLMs + RAG can:
  - Read code PDFs and extract relevant clauses.
  - Work against structured schedule data (CSV).
  - Produce explainable issue lists with references.
- A simple, scoped MVP can prove value without full BIM integration or heavy frontend tooling.

---

## 3. Users and Use Cases

### 3.1 Primary users

- **Architect / Designer**

  - Works in Revit/AutoCAD but uses this tool as an external checker.
  - Wants quick feedback on “Is this layout roughly code-clean?”

- **Technical Architect / Coordinator**
  - Responsible for code compliance reviews.
  - Wants a pre-check tool before formal review.

### 3.2 Core use cases

1. **Quick compliance snapshot**

   - User loads the built-in sample project.
   - System returns an issues list: which rooms/doors/corridors are non-compliant and why.

2. **Explain a specific violation**

   - User clicks “Room 101” in the issues list.
   - System explains:
     - Which rule was violated.
     - What the requirement is.
     - Where it comes from (code reference).

3. **Answer code Q&A**

   - User asks, “What is the minimum corridor width for these office levels?”
   - System:
     - Retrieves relevant code text.
     - Answers and cites the source.
     - Optionally relates it to current corridors.

4. **What-if questions (lightweight)**
   - User asks: “If I increase Room 101 to 12 m², will it be compliant?”
   - System checks rule threshold vs 12 m² and answers yes/no.

---

## 4. Inputs and Outputs

### 4.1 Inputs

- **Floor plan image**

  - `plan.png`
  - 2D floor plan, single floor, used purely for visualization.

- **Design data (CSV)**

  - `rooms.csv`
    - Columns: `id`, `name`, `type`, `level`, `area_m2`
  - `doors.csv`
    - Columns: `id`, `location_room_id`, `clear_width_mm`, `level`
  - (Corridors optional for MVP; can be derived or hard-coded for demo.)

- **Overlay geometry (JSON)**

  - `overlays.json`
    - For each room/door:
      - `id`, `type`, `x`, `y`, `width`, `height` (image pixel coords)

- **Code / standards (PDF)**
  - Multiple PDFs supported:
    - `National-Building-Code.pdf`
    - `RA9514-RIRR-rev-2019-compressed.pdf`
    - Additional PDFs can be added
  - Contains relevant clauses on:
    - Minimum room area for specific types.
    - Minimum door clear width.
    - Minimum corridor width.
  - Rules are extracted via LLM (`rule_extractor.py`) with project context filtering to reduce false positives.

### 4.2 Outputs

- **Issues list (structured)**

  - Array of `Issue` objects:
    - `id`: string
    - `element_type`: `"room" | "door"`
    - `element_id`: string (`Room.id` or `Door.id`)
    - `rule_id`: string
    - `message`: human-readable description
    - `severity`: `"error" | "warning"`
    - `code_ref`: string (doc/page/section)

- **Chat responses**

  - Natural language answers with:
    - Short summary.
    - Optional bullet list of affected elements.
    - Code citations where applicable.

- **Plan highlights**
  - When an issue is selected, the corresponding overlay is highlighted on the plan (using CSS/DOM manipulation, no framework).

---

## 5. Core Functionality (MVP)

### 5.1 Backend

**Stack:** Python 3.11+, FastAPI, LangChain/LangGraph, OpenAI (primary), Qdrant or in-memory vector store, BM25 retrieval (validated best for building codes).

1. **Health endpoint**

   - `GET /health`
   - Returns `{"status":"ok"}`

2. **Design data loading**

   - Service: `design_loader.py`
   - Functions:
     - `load_rooms() -> list[Room]`
     - `load_doors() -> list[Door]`

3. **Rule models (seeded)**

   - `Rule` pydantic model:
     - `id`, `applies_to`, `attribute`, `operator`, `threshold`, `units`, `description`, `source`
   - `rules_seed.py`:
     - At least:
       - `ROOM_OFFICE_MIN_AREA`
       - `DOOR_MIN_CLEAR_WIDTH`
       - (Optional) `CORRIDOR_MIN_CLEAR_WIDTH`

4. **Compliance checker**

   - Service: `compliance_checker.py`
   - `check_compliance(rooms, doors, rules) -> list[Issue]`
   - Simple numeric comparisons:
     - `area_m2 >= threshold`
     - `clear_width_mm >= threshold`

5. **Issues endpoint**

   - `GET /api/issues`
   - Pipeline:
     - `rooms = load_rooms()`
     - `doors = load_doors()`
     - `rules = get_all_rules()` (combines seeded + LLM-extracted rules)
     - `issues = check_compliance(...)`
   - Returns `Issue[]` as JSON.

6. **LLM-based Rule Extraction** (Core MVP Feature)

   - `rule_extractor.py`:
     - Extracts structured `Rule` objects from building code PDFs using LLM
     - Project context filtering (e.g., residential vs commercial, single-story vs multi-story)
     - Filters extracted rules based on project characteristics to reduce false positives
     - Combines with seeded rules for comprehensive rule set
     - Uses LLM cache to reduce API costs and latency

7. **RAG pipeline over code PDFs**

   - `pdf_ingest.py`:
     - `extract_pdf_chunks(pdf_path) -> list[{content, page, source}]`
     - Enhanced metadata: `source`, `chunk_index`, `page_pdf`, `page_document`, `page`, `section`
   - `vector_store.py`:
     - `ensure_collection()`
     - `index_chunks(chunks)`
     - `search(query, top_k=3) -> [{content, source, score}]`
     - **BM25-only retrieval** (validated via RAGAS evaluation: composite score 0.422)
     - Supports multiple PDFs (not just single `code_sample.pdf`)
   - `llm.py`:
     - Wrapper over OpenAI (configurable provider).
     - LLM response caching (in-memory or SQLite)

8. **Chat endpoint**

   - `POST /api/chat`
   - Input:
     - `query: str` (single query string, not full message history)
   - Behavior:
     - Uses **BM25 retrieval** for code-related questions
     - Retrieves relevant code snippets from PDFs
     - Calls LLM with:
       - System prompt: "code-aware space planning assistant"
       - Context: retrieved snippets with citations
     - Returns:
       - `answer`: Natural language response
       - `citations`: Array of citation objects with `source`, `page`, `section`, `text`
   - Includes project context in responses when relevant.

9. **HTML UI + static file serving**
   - Use FastAPI `StaticFiles` for:
     - `/static/plan.png`
     - `/static/styles.css`
     - `/static/overlays.json` (fully implemented, not optional)
   - Use FastAPI `Jinja2Templates` for:
     - `GET /` → returns `index.html` template (no React, no bundler).

### 5.2 UI (served by FastAPI, no Node/npm)

**Stack:** Plain HTML + CSS + minimal inline JS.

1. **App layout (single template)**

   - Template: `app/templates/index.html`
   - Layout:
     - Left: plan viewer.
     - Bottom of left: issues list.
     - Right: chat panel.
   - CSS in `app/static/styles.css`.

2. **Plan viewer**

   - `<img src="/static/plan.png">` as background.
   - Overlay elements (fully implemented):
     - `<div>`s absolutely positioned over the image based on `overlays.json` (fetched by browser JS).
     - Supports both room and door overlays
     - Dynamic scaling and positioning based on image dimensions
   - When an issue is selected, matching `id` is highlighted with red border and pulsing animation.

3. **Issues list**

   - Uses browser `fetch('/api/issues')` after page load.
   - Renders each issue as a simple block:
     - Element type + id
     - Message
     - Code reference
   - On click:
     - Saves selected `element_id` and triggers highlight in plan viewer.

4. **Chat panel**

   - Simple `<textarea>` + `<button>` inside a `<form>`.
   - On submit:
     - Prevent default.
     - `fetch('/api/chat')` with `query` string (single message, not history).
   - Renders messages as a vertical list:
     - "You: …"
     - "AI: …" (with citations displayed when available)

5. **No build toolchain**
   - No `npm install`, no `package.json`, no Vite, no React.
   - All JS is inline in `index.html` (or simple `.js` under `/static` if needed).
   - All assets are served by FastAPI.

---

## 6. Non-Goals (MVP)

- No real CAD/BIM model parsing (IFC, Revit API, etc.).
- No automatic geometry detection from `plan.png`.
- No authentication or multi-user accounts.
- No persistence of user-specific projects.
- No full code-completeness of building codes (only small subset used).
- No React, no SPA framework, no Node/npm-based build tooling.
- No websocket-based live updates (simple request/response only).

---

## 7. System Architecture (High Level)

### 7.1 Components

- **FastAPI application**

  - `app/main.py`
    - Mounts static files.
    - Configures templates.
    - Registers API routers.
    - Serves `GET /` → HTML UI.
  - `app/api/issues.py`
  - `app/api/chat.py`
  - Services:
    - `design_loader.py`
    - `pdf_ingest.py`
    - `vector_store.py`
    - `compliance_checker.py`
    - `rules_seed.py`
    - `rule_extractor.py` (LLM-based rule extraction with project context filtering)
  - Core:
    - `llm.py` (LLM wrapper with caching)
  - Models:
    - `domain.py` (Room, Door, Rule, Issue)

- **Vector DB**

  - Qdrant (local or cloud)
  - Collection: `code_chunks`

- **Browser**
  - Loads `index.html` from FastAPI.
  - Uses `fetch` API to call:
    - `/api/issues`
    - `/api/chat`
  - Manipulates DOM to render issues and chat messages.
  - Optional: manipulates DOM to apply overlay highlights.

### 7.2 Data flow: compliance

1. Browser loads `/`.
2. Browser JS calls `/api/issues`.
3. Backend:
   - Loads CSV → Rooms/Doors.
   - Gets all rules:
     - Seeded rules from `rules_seed.py`
     - LLM-extracted rules from PDFs via `rule_extractor.py` (with project context filtering)
   - Runs `check_compliance`.
   - Returns `Issue[]`.
4. Browser:
   - Renders issues list.
   - On click, highlights corresponding element in plan viewer (red border with pulsing animation).

### 7.3 Data flow: Q&A

1. User types question in chat and submits form.
2. Browser sends POST to `/api/chat` with `query` string.
3. Backend:
   - Uses BM25 retrieval to search code PDFs.
   - Retrieves top-k relevant chunks with metadata (source, page, section).
   - Calls LLM with:
     - System prompt: "code-aware space planning assistant"
     - Context: retrieved code snippets
     - User query
   - Returns:
     - `answer`: Natural language response
     - `citations`: Array of citation objects
4. Browser displays reply with citations.

---

## 8. Data Model Definitions

### 8.1 Room

```python
class Room(BaseModel):
    id: str
    name: str
    type: str
    level: Optional[str] = None
    area_m2: float
```
````

### 8.2 Door

```python
class Door(BaseModel):
    id: str
    location_room_id: Optional[str] = None
    clear_width_mm: float
    level: Optional[str] = None
```

### 8.3 Rule

```python
class Rule(BaseModel):
    id: str
    applies_to: Literal["room", "door", "corridor"]
    attribute: str            # e.g. "area_m2", "clear_width_mm"
    operator: Literal[">=", ">", "<=", "<", "=="]
    threshold: float
    units: str
    description: str
    source: str               # e.g. "Code.pdf p.7, Sec 5.1"
```

### 8.4 Issue

```python
class Issue(BaseModel):
    id: str
    element_type: Literal["room", "door"]
    element_id: str
    rule_id: str
    message: str
    severity: Literal["error", "warning"] = "error"
    code_ref: str
```

---

## 9. Constraints and Assumptions

- **Units:** All internal logic uses SI:

  - Areas in m².
  - Widths in mm (or m, but consistent within rules and data).

- **Data quality:** CSVs are clean and predictable for MVP.
- **PDF content:** Contains the rules we seed; RAG is a supporting feature, not the sole source of truth for compliance.
- **LLM:** Access to at least one hosted LLM (OpenAI, Gemini, or Claude) with enough context window for small PDFs.
- **Frontend:** No Node/npm. Only browser-native APIs and static assets.

---

## 10. MVP Feature Checklist

Backend:

- [x] `/health`
- [x] CSV loaders for rooms and doors
- [x] Seeded rules in `rules_seed.py`
- [x] LLM-based rule extraction from PDFs (`rule_extractor.py`) with project context filtering
- [x] `check_compliance()` producing `Issue[]`
- [x] `/api/issues` returning issues
- [x] PDF ingest + vector store indexing (BM25-only retrieval)
- [x] `/api/chat` combining issues + RAG with citations
- [x] Static + template setup for `GET /`
- [x] Deployment configuration (Dockerfile, Railway config)

UI:

- [x] Basic layout in `index.html` (left viewer, bottom issues, right chat)
- [x] Plan viewer with `plan.png`
- [x] Overlays and highlight behavior (fully implemented - room and door overlays with red highlight)
- [x] Issues list fetching `/api/issues`
- [x] Chat form posting to `/api/chat` and rendering replies with citations

---

## 11. Risks and Mitigations

1. **LLM hallucinating code requirements**

   - Mitigation:

     - Seed rules explicitly.
     - Use LLM for explanations and Q&A, not as sole source of numeric thresholds.
     - Emphasize “Do not invent rules” in system prompt.

2. **RAG retrieval irrelevant / noisy**

   - Mitigation:

     - Limit to few chunks.
     - Filter by score.
     - Keep PDFs small and curated for MVP.

3. **Time overruns**

   - Mitigation:

     - Hard prioritize Phases 0–6 (basic backend + HTML UI + simple chat).
     - **Status:** LLM-based rule extraction implemented as core MVP feature with project context filtering to reduce false positives.

4. **Frontend complexity creep**

   - Mitigation:

     - No frameworks, no bundlers.
     - Only minimal DOM manipulation with browser `fetch` and vanilla JS.

---

## 12. Evaluation

### 12.1 Functional

- Given the sample CSVs and multiple code PDFs:

  - The system correctly flags:

    - A room with area below threshold (R101: 8.5 m² < 9.5 m² minimum).
    - Doors with width below threshold (D1, D2, D3, D4 violations).
    - Project context filtering reduces false positives (28 → 3 issues in test case).

- Chat:

  - Can list all current issues accurately.
  - Can explain why a specific element is non-compliant.
  - Can answer at least 3 code-related questions with matching snippets from multiple PDFs.
  - Returns citations with source, page, and section information.

### 12.2 UX

- Architect can:

  - Open one URL (`/`) and see layout without any installation beyond Python deps.
  - See issues at a glance in the list.
  - Click an issue and visually relate it to the plan.
  - Ask follow-up questions in chat without re-explaining the whole context.

### 12.3 Technical

- Backend and UI start with simple commands:

  - `uvicorn app.main:app --reload`
  - Or deploy via Railway.app / Docker

- No Node/npm on the machine.
- BM25 retrieval returns relevant code snippets for basic queries (validated via RAGAS: composite score 0.422).
- LLM caching reduces API costs and latency.
- End-to-end testing: 16/16 tests passing (100% success rate).
- No critical errors in logs during demo.

---

```
::contentReference[oaicite:0]{index=0}
```
