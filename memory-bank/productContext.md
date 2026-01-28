# Product Context

Target users:

- Architects and designers working on early-stage layouts for vertical buildings.

Primary problem:

- Manually checking room areas, door widths, and corridor widths against building codes and internal standards is slow and error-prone.

**Key pain points:**

1. **Multiple jurisdictions, multiple codes**: Architects work across different locations, each with its own building code (e.g., National Building Code of Philippines, IBC, local codes). They must read and familiarize themselves with many different code documents, which is time-consuming.

2. **Code complexity**: Building codes are dense, technical documents. Finding relevant requirements for specific design elements (room sizes, door widths) requires extensive reading and cross-referencing.

3. **Manual checking**: Verifying compliance involves manually comparing design values against code requirements, which is slow and error-prone.

**Why LLM/RAG solves this:**

- **RAG (Retrieval-Augmented Generation)**: Can ingest multiple building code PDFs and answer questions about requirements without requiring architects to read entire documents.

- **Rule extraction**: LLM can automatically extract structured rules from code PDFs, reducing the need to manually identify and codify requirements.

- **Multi-code support**: The system can handle multiple code documents simultaneously (pre-loaded + user-uploaded), allowing architects to check against different jurisdictions without switching contexts. Users can upload their own building code PDFs via the Upload Building Codes tab, and these PDFs are immediately available for both chat queries and compliance checking.

Inputs:

- Floor plan image (plan.png).
- CSV schedules:
  - rooms.csv (id, name, type, level, area_m2)
  - doors.csv (id, location_room_id, clear_width_mm, level)
- Building code PDFs (code_sample.pdf).
- overlays.json for room/door polygons on plan image.

Core features (MVP):

- Backend endpoint /api/issues:
  - loads CSVs and seeded Rule models,
  - runs compliance_checker,
  - returns Issue[] with element_id, rule_id, message, code_ref.
- Backend endpoint /api/chat (Conversational with Blueprint Context):
  - maintains conversation history per conversation_id (in-memory for MVP),
  - integrates extracted blueprint room data for context-aware responses,
  - combines RAG results from code PDFs (pre-loaded + uploaded) with current issues,
  - answers questions about code requirements and current design issues,
  - supports follow-up questions (e.g., "What about bathrooms?" after asking about bedrooms),
  - can reference specific rooms from uploaded blueprints.
- Backend endpoint /api/codes/upload/:
  - accepts PDF file uploads,
  - ingests and indexes PDFs for RAG queries,
  - saves to persistent storage (`app/data/uploads/`) for compliance checking,
  - uploaded PDFs immediately available for chat queries and rule extraction.
- Frontend (single-page HTML/CSS/JS served directly by FastAPI):
  - Plan viewer with overlay highlighting when an issue is selected.
  - Issues list panel below viewer.
  - Right panel with three tabs:
    - "💬 Q&A Chat" - Conversational chat with blueprint context integration
    - "🔍 Blueprint Extraction" - Upload and extract rooms from blueprint images
    - "📚 Upload Building Codes" - Upload custom building code PDFs
  - No separate frontend server or build process; all served from `GET /` endpoint.

Success criteria:

- Returns correct violations for a small sample dataset.
- Conversational chat can:
  - maintain conversation history across messages,
  - support follow-up questions with context,
  - integrate with extracted blueprint data for context-aware responses,
  - list current issues,
  - explain why a room/door is non-compliant,
  - quote relevant code text when available (from pre-loaded and uploaded PDFs).
- PDF upload enables:
  - users to upload custom building code PDFs,
  - immediate availability for RAG queries,
  - automatic inclusion in compliance rule extraction,
  - multi-jurisdiction support.

## Project Intent & Learning Goals

This project serves dual purposes:

1. **Bootcamp demo**: Showcase a working MVP that demonstrates AI/LLM integration in an AEC domain application.

2. **Learning project**: Deep understanding of the codebase, not just accepting AI-generated code.

**Learning objectives:**
- Understand architectural decisions and tradeoffs
- Learn patterns from `internal/lessons/` as reference examples, not templates to clone
- Build comprehension of FastAPI, LangChain/LangGraph, RAG pipelines, and vector stores
- Develop ability to reason about code structure and make informed choices

**Working style:**
- Explanations and rationale are essential when implementing features
- Break down complex patterns so they can be understood, not just copied
- Encourage questions and discussion about design decisions
- Code should be clear and well-structured to support learning