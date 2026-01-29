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

1. **Data Flow (CAD → Compliance)**
   - CAD Software (CSV proxy) → Design Loader → Compliance Checker → Issues API
   - In production: Direct CAD integration (AutoCAD/Revit APIs)

2. **RAG Flow (PDF → Chat)**
   - Building Code PDFs (pre-loaded + uploaded) → PDF Ingest → Embedding Model → Vector Store → Chat API
   - BM25 retrieval (validated best for building codes)
   - Uploaded PDFs saved to persistent storage for compliance checking

3. **LLM Flow (Rule Extraction + Chat)**
   - Rule Extractor/Chat API → LLM Client → Cache → OpenAI API
   - Caching reduces API costs and latency

4. **Frontend (CAD UI Proxy)**
   - Plan Viewer, Issues List, Chat Panel
   - In production: Embedded within CAD software UI

**Design Decisions:**
- BM25-only retrieval (validated via RAGAS: composite score 0.422)
- Project context filtering (reduces irrelevant rules: 28 → 3 issues)
- Multi-layer caching (CSV, embeddings, LLM responses)

*See `docs/architecture-diagram.md` for detailed diagram*

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

### Live Demo: Compliance Checking + RAG Chat

**Demo Flow:**

1. **Context**: Explain MVP is proof-of-concept Add-In
   - CSV files represent data exported from AutoCAD/Revit
   - Web UI demonstrates functionality that would embed in CAD software

2. **Show Compliance Issues**
   - List of violations (room area, door width)
   - Click issue → red highlight on floor plan overlay

3. **Conversational Chat**
   - Ask: "What is the minimum bedroom area?"
   - RAG response with citations from building code PDFs
   - Ask follow-up: "What about bathrooms?"
   - System maintains conversation context
   - Ask: "Tell me about ramp width from [uploaded PDF]"
   - Demonstrates uploaded PDF integration

4. **PDF Upload**
   - Switch to "Upload Building Codes" tab
   - Upload a building code PDF
   - Show success message and indexing status
   - Demonstrate uploaded PDF is immediately searchable

5. **Visual Highlighting**
   - Select issue from list
   - Corresponding overlay highlights in red on plan
   - Shows exact location of violation

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