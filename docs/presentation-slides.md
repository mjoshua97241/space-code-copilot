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

1. **Automated Compliance Checking**
   - Loads design data (rooms, doors) from CAD software
   - Checks against extracted building code rules
   - Returns structured violations with code references

2. **RAG-Based Code Q&A**
   - Ingest building code PDFs
   - Answer questions about requirements
   - Provide citations with page numbers

3. **Visual Issue Highlighting**
   - Interactive floor plan viewer
   - Highlights non-compliant elements
   - Click issue → see highlighted area on plan

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
- ✅ 1-2 building code PDFs with RAG-based Q&A
- ✅ Automated compliance checking (room area, door width)
- ✅ Interactive plan viewer with issue highlighting
- ✅ Plain HTML/CSS/JS frontend (no build toolchain)
- ✅ Project context filtering (reduces false positives)

**What's Not Included (Post-MVP):**
- ❌ Real BIM/IFC parsing (CSV is proxy for CAD data)
- ❌ Multi-floor support
- ❌ Direct CAD integration (AutoCAD/Revit Add-In - future)
- ❌ Complex authentication/authorization
- ❌ Real-time collaboration
- ❌ Advanced RAG features (cross-encoder re-ranking, multi-hop retrieval)

**Current Status:** Proof-of-concept demonstrating core functionality for CAD Add-In integration

---

## Slide 5: Architecture

### System Architecture

**Key Components:**

1. **Data Flow (CAD → Compliance)**
   - CAD Software (CSV proxy) → Design Loader → Compliance Checker → Issues API
   - In production: Direct CAD integration (AutoCAD/Revit APIs)

2. **RAG Flow (PDF → Chat)**
   - Building Code PDFs → PDF Ingest → Embedding Model → Vector Store → Chat API
   - BM25 retrieval (validated best for building codes)

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

3. **Interactive Chat**
   - Ask: "What is the minimum bedroom area?"
   - RAG response with citations from building code PDFs
   - Ask: "Why is room R101 non-compliant?"
   - Context-aware answer referencing current issues

4. **Visual Highlighting**
   - Select issue from list
   - Corresponding overlay highlights in red on plan
   - Shows exact location of violation

**Key Features Demonstrated:**
- Automated compliance checking
- RAG-powered code Q&A
- Visual issue highlighting
- Add-In architecture concept

---

## Slide 8: Takeaways

### Key Achievements & Future Enhancements

**What We Built:**
- ✅ Automated compliance checker with rule extraction
- ✅ RAG-based building code Q&A with citations
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
- **Slide 7 (Demo)**: 2.5 minutes
- **Slide 8 (Takeaways)**: 30 seconds

### Key Talking Points

1. **Emphasize Add-In architecture**: This is not just a web app—it's designed to integrate into CAD software
2. **Highlight validation**: BM25 retrieval was validated via RAGAS evaluation
3. **Show real results**: 6 compliance issues found, RAG answers with citations
4. **Demonstrate interactivity**: Click issue → see highlight on plan

### Q&A Preparation

- **Technical**: BM25 retrieval, project context filtering, caching strategy
- **Scalability**: Multi-jurisdiction support, performance optimizations
- **Future**: CAD integration, user-provided API keys, advanced features