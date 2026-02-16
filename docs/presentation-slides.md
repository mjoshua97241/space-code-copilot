# Presentation Slides - Code-Aware Space Planning Copilot

## Slide 1: Title

# Code-Aware Space Planning Copilot
### AI-Powered Building Code Compliance for AEC

**MVP: Proof-of-Concept CAD Add-In**

---

## Slide 2: Problem

### The Challenge: Manual Building Code Compliance

**Pain Points:**

1. **Multiple Jurisdictions, Multiple Codes**
   - Architects work across different locations
   - Each location has its own building code (NBC, IBC, local codes)
   - Time-consuming to read and familiarize with many documents

2. **Code Complexity**
   - Dense, technical documents (hundreds of pages)
   - Finding relevant requirements requires extensive reading
   - Cross-referencing across sections is error-prone

3. **Manual Checking**
   - Verifying compliance: manually comparing design values vs. code requirements
   - Slow, error-prone, doesn't scale

**Result:** Architects spend hours checking room areas, door widths, and corridor dimensions against building codes

---

## Slide 3: Solution

### Automated Compliance + RAG-Powered Chat

**Core Features:**

1. **VLM-Based Blueprint Extraction & Compliance**
   - Extracts structured room data directly from blueprint images using Vision LLM
   - Semantic understanding: reads room labels, classifies types, associates dimensions
   - Editable areas for user correction
   - Integrated compliance checking on extracted data (seeded + LLM-extracted rules from PDFs)
   - Returns structured violations with code references
   - Eliminates need to manually create CSV schedules (CSV path still available for plan viewer / issues list)

2. **Conversational RAG-Based Code Q&A**
   - Ingest building code PDFs (pre-loaded + user-uploaded)
   - Answer questions about requirements with conversation history
   - Integrates with extracted blueprint room data for context-aware responses
   - Provide citations with page numbers
   - Supports follow-up questions and context-aware answers

3. **PDF Upload for Custom Building Codes**
   - Users can upload their own building code PDFs
   - Uploaded PDFs immediately indexed for RAG queries
   - Uploaded PDFs included in compliance rule extraction
   - Enables multi-jurisdiction support

*Deferred (not in core features):* Visual issue highlighting on plan (click issue → see highlighted area) — backend/overlays ready, frontend rendering deferred.

**MVP Context:**
- **This is a proof-of-concept Add-In for CAD software (AutoCAD/Revit)**
- CSV files = proxy for data from CAD software
- Standalone web UI = proxy for UI embedded in CAD software
- Demonstrates core functionality that would integrate directly into CAD

---

## Slide 4: Scope & Limitations

### MVP Scope & Constraints

**What's Included:**
- ✅ Single floor plan with CSV schedules (rooms, doors)
- ✅ VLM-based blueprint extraction with integrated compliance checking (room area, door width)
- ✅ Pre-loaded + user-uploaded building code PDFs with RAG-based Q&A
- ✅ Conversational chat with blueprint context integration
- ✅ PDF upload tab for custom building codes
- ✅ Plain HTML/CSS/JS frontend (no build toolchain)
- ✅ Project context filtering (reduces false positives)

**What's Not Included (Post-MVP):**
- ❌ Real BIM/IFC parsing (CSV is proxy for CAD data)
- ❌ Multi-floor support
- ❌ Direct CAD integration (AutoCAD/Revit Add-In - future)
- ❌ Complex authentication/authorization
- ❌ Real-time collaboration
- ❌ Advanced RAG features (cross-encoder re-ranking, multi-hop retrieval)

**Deferred to Future:**
- ⏸️ Visual issue highlighting on plan (click issue → see highlighted area on plan; backend/overlays ready)
- ⏸️ Frontend rendering of VLM label overlays (backend complete, frontend rendering deferred)
- ⏸️ Hugging Face VLM evaluation (requires CUDA GPU, deferred to future GPU-based evaluation)

**Current Status:** Proof-of-concept demonstrating core functionality for CAD Add-In integration

---

## Slide 5: Architecture

### System Architecture

**Key Components:**

1. **Data Flow (CAD + Blueprint → Compliance)**
   - CSV (CAD proxy) → Design Loader → Compliance Checker
   - Blueprint API (VLM extraction) → Compliance Checker; Compliance → Issues API (responses)
   - In production: Direct CAD integration (AutoCAD/Revit APIs)

2. **RAG Flow (PDF → Vector Store → Chat / Rule Extractor)**
   - Building Code PDFs (pre-loaded + uploaded) → PDF Ingest → Embedding Model → Vector Store
   - Chat API and Rule Extractor query Vector Store (Q); Vector Store returns retrieved docs (R)
   - BM25 retrieval (validated best for building codes)
   - Uploaded PDFs saved to persistent storage for compliance rule extraction

3. **LLM Flow (Prompts P, Responses R)**
   - **Text LLM:** Rule Extractor / Chat API → prompts (P) → LLM; LLM → responses (R) → Rule Extractor / Chat API. LLM ↔ Cache ↔ OpenAI API.
   - **Vision LLM:** Blueprint API → prompts (P) → VLM; VLM → responses (R) → Blueprint API (Gemini 2.0 Flash default).
   - Caching reduces API costs and latency

4. **Frontend (CAD UI Proxy)**
   - Left: Plan Viewer, Issues List. Right: Tabs — Q&A Chat, Blueprint Extraction, Upload Building Codes
   - In production: Embedded within CAD software UI

**Design Decisions:**
- BM25-only retrieval (validated via RAGAS: composite score 0.422)
- Project context filtering (reduces irrelevant rules: 28 → 3 issues)
- Multi-layer caching (CSV, embeddings, LLM responses)
- Diagram edge types: D (data/indexing), P (prompts), Q (queries), R (responses), BC (blueprint context)

*See `docs/architecture-diagram.md` for detailed and simplified diagrams*

---

## Slide 6: Metrics

### Performance & Quality Metrics

**System Performance:**
- ✅ **16/16 end-to-end tests passing** (100% success rate)
- ✅ **Deployed to Railway.app** (public URL available)
- ✅ **All features working**: Compliance checking, RAG chat, overlays

**RAG Quality:**
- **BM25-only retrieval validated** (composite score: 0.422)
- Building codes benefit from exact term matching over semantic similarity
- Citations include explicit page type indicators (PDF page vs. document page)

**Rule Extraction:**
- **6 rules extracted** from 2 building code PDFs
- Project context filtering: **28 issues → 3 issues** (removed irrelevant commercial/multi-story rules)
- Room type-specific matching (bedroom rules only apply to bedrooms)

**Caching Strategy:**
- CSV: `@lru_cache` for file-based caching
- Embeddings: File-based cache
- LLM: SQLite/Memory cache (reduces redundant API calls)

---

## Slide 7: Demo

### Live Demo: Three Highlights of the Solution

**Demo Flow:**

1. **Context**
   - MVP is proof-of-concept Add-In for CAD (AutoCAD/Revit)
   - CSV and standalone web UI = proxy for CAD data and embedded UI

2. **Highlight 1: VLM-Based Blueprint Extraction & Compliance**
   - Go to "Blueprint Extraction" tab
   - Upload a blueprint image or PDF
   - VLM extracts rooms (name, type, area); show results with editable area fields
   - Optionally correct an area, then run "Check Compliance" on extracted data
   - Show issues list with code references (deterministic check, rules from seeded + LLM-extracted PDFs)
   - Emphasize: no manual CSV; extraction + compliance in one flow

3. **Highlight 2: Conversational RAG-Based Code Q&A**
   - Go to "Q&A Chat" tab
   - Ask: "What is the minimum bedroom area?" — RAG response with citations from building code PDFs
   - Follow-up: "What about bathrooms?" — system maintains conversation context
   - If blueprint was extracted: ask with blueprint context (e.g. "Is bedroom 1 compliant?") — shows context-aware answer using extracted room data
   - Ask about a requirement from an uploaded PDF (bridges to Highlight 3)

4. **Highlight 3: PDF Upload for Custom Building Codes**
   - Switch to "Upload Building Codes" tab
   - Upload a building code PDF (e.g. local or alternate jurisdiction)
   - Show success message; explain PDF is indexed for RAG and for rule extraction
   - Return to Chat; ask a question that requires the newly uploaded PDF — demonstrates immediate searchability and multi-jurisdiction support

*Note:* Visual issue highlighting on plan (click issue → red overlay) is deferred; backend/overlays ready, frontend rendering later. Demo focuses on issues list and the three core features above.

**Key Features Demonstrated:**
- Automated compliance checking
- VLM-based blueprint extraction (semantic understanding)
- Conversational RAG-powered code Q&A with blueprint context
- PDF upload for custom building codes
- Visual issue highlighting
- Add-In architecture concept

---

## Slide 8: Takeaways

### Key Achievements & Future Enhancements

**What We Built:**
- ✅ Automated compliance checker with rule extraction
- ✅ VLM-based blueprint extraction (semantic room extraction from images)
- ✅ Conversational RAG-based building code Q&A with citations
- ✅ Blueprint context integration (extracted rooms in chat)
- ✅ PDF upload for custom building codes (multi-jurisdiction support)
- ✅ Interactive floor plan viewer with issue highlighting
- ✅ Project context filtering (reduces false positives)
- ✅ Validated BM25 retrieval for building codes
- ✅ End-to-end tested and deployed

**Future Enhancements:**
1. **Direct CAD Integration**
   - AutoCAD/Revit Add-In (no CSV export needed)
   - Real-time design data extraction
   - Embedded UI panels within CAD software

2. **User-Provided API Keys**
   - Users can use their own OpenAI/Gemini credits
   - Eliminates server costs
   - Prevents API key abuse

3. **Advanced Features**
   - Multi-jurisdiction support
   - Custom rule sets
   - Batch compliance checking
   - Export compliance reports

4. **Frontend Overlay Rendering**
   - VLM label overlays rendering in plan viewer (backend complete, frontend deferred)
   - Visual highlighting of non-compliant rooms using VLM-generated overlays
   - Integration with existing overlay rendering system

5. **Hugging Face VLM Evaluation**
   - GPU-based evaluation of HF VLM models (currently deferred, requires CUDA)
   - Colab runner available for future GPU evaluation

6. **Blueprint Data Storage & Embedding**
   - Currently, blueprint extraction results are passed directly in chat requests
   - For multi-blueprint search capabilities, consider embedding structured room data
   - Enable queries like "Find all bedrooms larger than 20m² across all projects"
   - Cross-project room similarity search and historical blueprint analysis
   - **Note**: Current MVP uses direct pass-through (simpler, sufficient for single-blueprint sessions)
   - Would require different embedding strategy than text documents (structured data vs. unstructured text)
   - Consider separate structured data store (database) vs. vector store depending on use case

**Short version (for slide bullets):**
- **CAD integration:** Add-In for AutoCAD/Revit; real-time data; embedded UI
- **User API keys:** Own OpenAI/Gemini credits; lower cost; no key abuse
- **Advanced:** Multi-jurisdiction; custom rules; batch check; export reports
- **Overlays:** VLM labels in plan viewer (backend done, frontend deferred)
- **HF VLM eval:** GPU evaluation deferred; Colab runner for later; if it surpasses current models we will integrate it
- **Blueprint storage:** Multi-blueprint search via structured room data (separate store); MVP uses pass-through

**MVP Status:** Ready for CAD software integration

---

## Presentation Notes

### Timing (7 minutes total)

- **Slide 1 (Title)**: 10 seconds
- **Slide 2 (Problem)**: 1 minute
- **Slide 3 (Solution)**: 45 seconds
- **Slide 4 (Scope & Limitations)**: 30 seconds
- **Slide 5 (Architecture)**: 1.5 minutes
- **Slide 6 (Metrics)**: 1 minute
- **Slide 7 (Demo)**: 2.5 minutes (includes blueprint extraction, conversational chat, and PDF upload)
- **Slide 8 (Takeaways)**: 30 seconds

### Key Talking Points

1. **Emphasize Add-In architecture**: This is not just a web app—it's designed to integrate into CAD software
2. **Highlight validation**: BM25 retrieval was validated via RAGAS evaluation; VLM model (Gemini 2.0 Flash) selected via evaluation
3. **Show real results**: Compliance issues found, VLM extraction results, conversational RAG answers with citations
4. **Demonstrate interactivity**: Click issue → see highlight on plan, upload blueprint → extract rooms → check compliance, follow-up questions work, PDF upload integrates seamlessly
5. **Show multi-jurisdiction support**: Upload PDFs from different jurisdictions, immediately available for queries and compliance
6. **Highlight VLM capabilities**: Semantic understanding of blueprints (not just OCR), room type classification, dimension association

### Q&A Preparation

- **Technical**: BM25 retrieval, project context filtering, caching strategy
- **Scalability**: Multi-jurisdiction support, performance optimizations
- **Future**: CAD integration, user-provided API keys, advanced features

---

## Possible Q&A: Questions and Answers

*Structure: each answer has a short **hook**, then **2–3 talking points** you can memorize.*

---

### Technical & Architecture

**Q: Why BM25 instead of pure semantic/dense retrieval for building codes?**

**A:**  
- **Hook:** We validated retrieval with RAGAS; BM25 won.  
- **1.** Building codes rely on exact terms (section numbers, legal phrases); BM25 matches those well.  
- **2.** Our RAGAS run showed BM25-only had the best composite score (0.422) vs hybrid or dense-only.  
- **3.** So we use BM25-only for RAG; embeddings still back the vector store for future flexibility.

---

**Q: How do you keep compliance checking auditable and predictable?**

**A:**  
- **Hook:** Compliance is deterministic; LLMs only interpret codes to produce the rule set.  
- **1.** **Rule set** = seeded rules + LLM-extracted rules from PDFs (rule extraction runs once / on upload).  
- **2.** **Check step** = numeric only (e.g. room area vs rule min); no LLM at check time.  
- **3.** **Violations** = fixed message template + code_ref from the rule; same inputs → same issues.

---

**Q: What’s the difference between the Vision LLM and the Text LLM in this system?**

**A:**  
- **Hook:** VLM reads images; Text LLM reads text and answers.  
- **1.** **VLM (e.g. Gemini 2.0 Flash):** blueprint image/PDF → structured rooms (name, type, area). No CSV needed.  
- **2.** **Text LLM (e.g. OpenAI):** RAG over building code PDFs (chat, Q&A with citations) and rule extraction from PDFs.  
- **3.** Blueprint data is passed as context into chat so the Text LLM can answer questions about “your” plan.

---

### Compliance & Blueprint Extraction

**Q: Can users correct the VLM extraction before compliance runs?**

**A:**  
- **Hook:** Yes; we treat extraction as editable input.  
- **1.** Extracted rooms are shown with **editable area fields** in the UI.  
- **2.** User can change area (or keep it), then run “Check Compliance” on that data.  
- **3.** Compliance and chat use the corrected room list, so the system stays auditable.

---

**Q: Where do the compliance rules come from?**

**A:**  
- **Hook:** Two sources: seeded rules and LLM-extracted rules from PDFs.  
- **1.** **Seeded:** hardcoded rules (e.g. min bedroom area, door width) for known codes.  
- **2.** **Extracted:** rule extractor uses RAG + LLM on building code PDFs (app/data and uploads) to add rules with code_ref.  
- **3.** Compliance always runs against this combined set; no LLM at violation time.

---

### RAG, Chat & PDF Upload

**Q: How does conversation context work in chat?**

**A:**  
- **Hook:** We keep history per conversation and optionally pass blueprint context.  
- **1.** Each chat has a **conversation_id**; we store messages in memory per ID.  
- **2.** Follow-ups (e.g. “What about bathrooms?”) get previous messages so the model keeps context.  
- **3.** If the user extracted a blueprint, we can send **blueprint_context** (room list) so answers reference their plan.

---

**Q: What happens when I upload a new building code PDF?**

**A:**  
- **Hook:** It’s ingested once, then used for both RAG and rules.  
- **1.** PDF is chunked and **indexed into the vector store** → immediately available for RAG chat.  
- **2.** **Rule extractor** runs on it (with others) so new rules from that PDF can be used in compliance.  
- **3.** File is stored under app/data/uploads so it persists across restarts; supports multi-jurisdiction.

---

### Scope, Limitations & Future

**Q: Why is visual issue highlighting on the plan deferred?**

**A:**  
- **Hook:** Backend and overlays are ready; we deferred frontend rendering.  
- **1.** We return overlay data (e.g. VLM label bboxes) from the API.  
- **2.** Drawing them in the plan viewer (e.g. click issue → red highlight) is not yet implemented in the UI.  
- **3.** It’s the next logical step for UX; issues list and code refs are already there.

---

**Q: Is this only for one jurisdiction or one code?**

**A:**  
- **Hook:** No; the design supports multiple jurisdictions and custom codes.  
- **1.** **Pre-loaded** PDFs (e.g. NBC, fire code) plus **Upload Building Codes** for other documents.  
- **2.** Uploaded PDFs are indexed and used for both **RAG** and **rule extraction**.  
- **3.** Project context (building type, occupancy, etc.) filters which rules apply, so you can mix codes.

---

**Q: How would this plug into real CAD (AutoCAD/Revit)?**

**A:**  
- **Hook:** This MVP is a proxy for an Add-In; integration is the next step.  
- **1.** **Today:** CSV = export from CAD; web UI = stand-in for the Add-In panel.  
- **2.** **Later:** Add-In would call CAD APIs for live design data (no CSV export) and embed this UI in the CAD window.  
- **3.** Same backend (compliance, RAG, blueprint extraction) would drive the Add-In; we’d swap data source and host UI.

---

**Q: Why not put blueprint PDFs in the vector store?**

**A:**  
- **Hook:** The vector store is for building code text; blueprints are images.  
- **1.** **Current store:** text chunks from building code PDFs for RAG and rule extraction.  
- **2.** **Blueprint uploads:** we use the VLM to extract **structured room data**; that’s passed as context (e.g. blueprint_context), not as searchable document chunks.  
- **3.** **Future:** if we add multi-blueprint search, we’d consider a separate store (e.g. structured room data or image embeddings), not the same index as code text.

---

### Metrics & Validation

**Q: How did you choose the VLM (e.g. Gemini 2.0 Flash)?**

**A:**  
- **Hook:** We evaluated VLMs on extraction quality; Gemini 2.0 Flash performed best in our setup.  
- **1.** We ran **evaluation** (e.g. composite score, recall) on GPT-4o and Gemini 2.0 Flash.  
- **2.** Gemini 2.0 Flash had better composite score (e.g. 0.753 vs 0.743), better recall, and lower latency/cost.  
- **3.** HF/VLM evaluation (e.g. Colab, GPU) is deferred; if another model surpasses this, we’ll integrate it.