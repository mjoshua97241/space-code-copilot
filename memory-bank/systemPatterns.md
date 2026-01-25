# System Patterns

Backend patterns:

- FastAPI app in `app/main.py`:
  - Use `Path(__file__).parent` for absolute paths to static/templates directories.
  - Mount static files: `app.mount("/static", StaticFiles(directory=...))`
  - Setup templates: `Jinja2Templates(directory=...)`
- API routes in app/api/\*.py, mounted in app/main.py via include_router:
  - `app/api/issues.py` - Compliance issues endpoints (`GET /api/issues`, `GET /api/issues/summary`)
  - `app/api/chat.py` - RAG-based chat endpoint (`POST /api/chat`) with BM25-only retrieval (validated best), explicit page type indicators in citations, and post-processing to fix LLM citations
  - `app/api/blueprint.py` - Blueprint extraction endpoint (`POST /api/blueprint/extract`) - **Status**: ✅ **COMPLETE** - Accepts blueprint image upload (PNG/JPG/PDF), extracts room data using VLM, returns preview-only results, supports multi-page PDFs with optional page_index parameter
- Services in app/services/\*.py encapsulate:
  - design_loader (CSV → Room/Door models)
  - pdf_ingest (PDF → chunks) - **Status**: ✅ **COMPLETE** - Enhanced with page number extraction (PDF + document pages), section extraction, and metadata preservation
  - vector_store (embedding + Qdrant search) - **Status**: ✅ **BM25-only retrieval (default, validated)** - Evaluation shows BM25-only is best (composite score: 0.422), hybrid and dense-only available as options
  - compliance_checker (rules + design → issues)
  - rule_extractor (LLM-based rule extraction from PDFs; MVP core feature) - **Status**: ✅ **COMPLETE** - Integrated with project context filtering, uses BM25-only retrieval (default, validated best)
  - blueprint_extractor (image → structured room data via VLM) - **Status**: ✅ **ALL PHASES COMPLETE** - Semantic understanding extraction from blueprint images, room-only (name, type, area), preview-only results, multi-page PDF support, tested on 3 curated plans with ground truth CSVs, VLM evaluation framework complete, Gemini 2.0 Flash selected as default model (composite score: 0.753)
- LLM client abstraction in app/core/llm.py to swap OpenAI/Gemini/Claude. - **Status**: ✅ Complete, vision LLM support added (get_vision_llm() defaults to Gemini 2.0 Flash, also supports GPT-4o)

AI patterns:

- Use **BM25-Only RAG** for building-code questions (Validated via RAGAS evaluation):
  - **BM25 retrieval**: Catches exact terms, section numbers, citations (e.g., "Section 5.2.3", "minimum 800mm")
  - **Evaluation result**: BM25-only outperformed hybrid (BM25 + Dense), dense-only, and parent-document retrieval
  - **Composite score**: 0.422 (BM25-only) - best among 4 techniques evaluated
  - Why BM25-only: Building codes are term-heavy with exact legal phrasing; exact term matching outperforms semantic similarity for this domain
  - See `memory-bank/implementationPlan.md` for evaluation details
  - **Status**: `vector_store.py` defaults to BM25-only retrieval (updated based on evaluation results)
- Supports multiple code documents simultaneously (multi-jurisdiction support).
- Architects can query across different building codes without switching contexts.
- Use deterministic Python for simple numeric compliance (area, widths).
- Use LLM for:
  - summarizing issues
  - answering questions via RAG (handles multiple code documents)
  - extracting rules from PDFs (MVP core feature) - **COMPLETE** - automatically processes multiple code PDFs with project context filtering
  - extracting structured data from blueprint images (VLM) - **IN PROGRESS** - semantic understanding of room labels, type classification, dimension association, structured JSON output
- Use Vision LLM (VLM) for:
  - blueprint image analysis (semantic understanding, not just OCR)
  - room label reading and type classification
  - dimension annotation association with rooms
  - structured extraction (blueprint → Room models → compliance checking)
- **Deferred to post-MVP**: Cross-encoder re-ranking, multi-hop retrieval, conflict resolution, structured hierarchy parsing

## HF VLM Evaluation Pattern (Deferred)

- **Evaluation entrypoints**:
  - Local runner: `evaluation/vlm_evaluation.py`
  - Colab-friendly runner: `evaluation/vlm_evaluation_colab.py`
- **Constraint**: Current HF adapter (`evaluation/hf_vlm_wrapper.py`) relies on **Unsloth**, which requires a **CUDA-capable GPU**. On CPU-only machines, HF evaluation should be skipped with a clear message.
- **Recommendation**: Run HF evaluation on **Google Colab (GPU runtime)** or any CUDA machine; keep local evaluation focused on GPT‑4o and Gemini.

Frontend patterns:

- Single HTML template (`app/templates/index.html`) served by FastAPI via Jinja2Templates.
- Layout structure:
  - Left: plan viewer (`<img src="/static/plan.png">` + overlay `<div>`s positioned absolutely).
  - Bottom: issues list container.
  - Right: chat panel with form and message container.
- **Overlay System** (`app/static/overlays.json` + JavaScript):
  - Overlays defined in JSON with pixel coordinates (x, y, width, height) for rooms and doors
  - JavaScript loads overlays on page load, calculates scaling based on image dimensions
  - Overlays positioned absolutely over plan image, automatically scale on window resize
  - Highlight behavior: Clicking an issue in compliance list highlights matching overlay by `element_id`
  - CSS: Blue base state (rgba(13, 110, 253, 0.3)), red highlight state (#dc3545) with pulsing animation
  - Supports both room and door overlays (matched by element_id from issues)
- **Dynamic Overlay System** (upcoming - `.cursor/plans/blueprint_extraction_testing_and_dynamic_overlays_ac96230f.plan.md`):
  - Overlays generated dynamically from OCR + text positioning (vs static JSON)
  - Uses pytesseract/easyocr to extract text positions from blueprint images
  - Matches VLM-extracted room names to OCR text positions using fuzzy matching (rapidfuzz)
  - Infers room boundaries using image processing heuristics (OpenCV optional)
  - Integrated with compliance checking on extracted rooms from blueprint extraction
  - Non-compliant rooms automatically highlighted in red with pulsing animation
  - Works alongside static overlay system (supports both JSON and API-generated overlays)
- JavaScript (inline or minimal separate script):
  - On page load: `fetch('/api/issues/')` → render issues list, `fetch('/static/overlays.json')` → render overlays.
  - **Note**: API endpoints require trailing slashes (`/api/issues/`, `/api/chat/`) to match FastAPI router definitions (`@router.get("/")` with prefix).
  - On issue click: save `element_id`, highlight corresponding overlay in plan viewer (red pulsing border).
  - On chat submit: `fetch('/api/chat/', {method: 'POST', body: ...})` → render reply.
  - DOM manipulation: create/update elements for issues, messages, and overlays.
- CSS (`app/static/styles.css`): layout (flex/grid), styling, overlay states (base, hover, highlighted).
- Static assets served via FastAPI `StaticFiles` mount at `/static/`.

Plan/Act:

- For larger refactors, use PLAN first, then ACT to implement, to avoid uncontrolled code changes.

## Reusing past lessons

- internal/lessons/ may contain working examples from past bootcamp sessions.
- When generating new code for this project:
  - Prefer following the patterns defined in this file and in the current backend layout.
  - Look at internal/lessons/ only to copy small, relevant patterns (e.g., a vector_store abstraction, a LangGraph agent node) and then adapt them.
  - Do not import internal/lessons modules directly into production code.

### When to use lessons

**Don't use lessons for:**
- Simple/standard patterns (CSV parsing, basic FastAPI routes, Pydantic models)
- Standard Python libraries (csv, pathlib, etc.)
- Basic CRUD operations

## Caching Strategy

The project uses different caching strategies for different data types and operations:

### CSV Data Caching (`design_loader.py`)
- **Purpose**: Cache parsed Room/Door models from CSV files
- **Strategy**: Python's `@lru_cache` decorator
- **Why**: CSV files are read frequently (every `/api/issues` call), but parsing is fast
- **Implementation**: 
  - `load_rooms()` and `load_doors()` use `@lru_cache(maxsize=2)`
  - Cache key includes file path + modification time (auto-invalidation)
  - Returns tuples (hashable) for caching, converted to lists when needed
- **File**: `app/services/design_loader.py`

### PDF Processing Caching (Separate Files)
PDFs require more sophisticated caching due to expensive operations:

#### Embedding Cache (`vector_store.py`)
- **Purpose**: Cache expensive embedding computations
- **Strategy**: `CacheBackedEmbeddings` pattern from day_12 lesson
- **Why**: Embedding API calls are slow and expensive
- **Implementation**: 
  - Uses LangChain's `CacheBackedEmbeddings` with `LocalFileStore`
  - Caches embeddings in `./cache/embeddings/` directory
  - Automatically checks cache before calling embedding API
  - `CacheBackedEmbeddings` wrapper class implemented in `vector_store.py`
  - Integrated into `VectorStore` class initialization
- **File**: `app/services/vector_store.py` - ✅ **COMPLETE**

#### LLM Response Cache (`llm.py` + `chat.py`)
- **Purpose**: Cache LLM API responses
- **Strategy**: `setup_llm_cache()` pattern from day_12 lesson
- **Why**: LLM API calls are slow, expensive, and often have identical prompts
- **Implementation**:
  - Uses `InMemoryCache` (dev) or `SQLiteCache` (production)
  - Configured via `setup_llm_cache(cache_type="memory"|"sqlite")`
  - Caches at LangChain global level
  - `setup_llm_cache()` function implemented in `app/core/llm.py`
  - Automatically called in `app/api/chat.py` on module import (memory cache for MVP)
- **File**: `app/core/llm.py` + `app/api/chat.py` - ✅ **COMPLETE**

### Why Separate Caching Strategies?

| Data Type | Operation | Caching Strategy | File |
|-----------|-----------|------------------|------|
| **CSV** | File I/O + parsing | `lru_cache` (simple) | `design_loader.py` |
| **PDF embeddings** | Embedding API calls | `CacheBackedEmbeddings` (day_12) | `vector_store.py` |
| **LLM responses** | LLM API calls | `setup_llm_cache()` (day_12) | `llm.py` |

**Rationale**:
- CSV caching is simple (built-in Python decorator)
- PDF/LLM caching uses day_12 lesson patterns (production-ready, handles expensive operations)
- Separation of concerns: each file handles its own caching needs
- Reusability: `llm.py` cache is shared across multiple services

### Cache Invalidation

- **CSV cache**: Invalidates automatically when file modification time changes
- **Embedding cache**: Persistent file-based cache (survives restarts)
- **LLM cache**: Memory cache (cleared on restart) or SQLite (persistent)

**Do use lessons for:**
- `app/services/vector_store.py` - RAG/vector DB patterns (Qdrant setup, embedding pipelines)
- `app/core/llm.py` - Multi-provider LLM abstraction (OpenAI/Gemini/Claude switching), vision LLM support (GPT-4o, Gemini 1.5 Flash Vision)
- `app/services/rule_extractor.py` - LLM-based extraction patterns (structured output, prompt engineering)
- `app/services/blueprint_extractor.py` - VLM-based extraction patterns (semantic understanding, structured output from images)
- `app/services/pdf_ingest.py` - PDF chunking patterns (if complex chunking strategies needed)
- LangGraph agent orchestration (if we add agent workflows)

**Decision process:**
1. If it's a standard Python/library pattern → implement directly
2. If it's LLM/AI-specific and complex → check lessons for patterns
3. Use `/use-lesson-pattern` command when explicitly requested

## Metrics and Observability

**Metrics implementation patterns from lessons:**

- **LangSmith** (day_12 lesson): Tracing and monitoring for LLM calls
  - Setup in `app/core/llm.py` or `app/main.py`
  - Automatic tracing of all LangChain calls
  - Tracks: token usage, latency, cost, retrieval quality
  - See `memory-bank/presentation.md` for implementation details

- **RAGAS** (day_13 lesson): Evaluation framework for RAG systems
  - Optional: For testing/evaluation of RAG quality
  - Metrics: faithfulness, answer relevancy, context precision, context recall
  - See `memory-bank/presentation.md` for implementation details

- **Performance metrics**: API response times, cache hit rates
  - FastAPI middleware for response time tracking
  - Cache statistics in service layer
  - See `memory-bank/presentation.md` for implementation details

**Metrics endpoint:**
- Optional `GET /api/metrics/summary` endpoint for presentation
- Returns: issue counts, cache stats, LLM call counts
- See `memory-bank/presentation.md` for example implementation

### Where to Implement Metrics in MVP

**1. LangSmith Setup** → `app/core/llm.py`
- Add `setup_langsmith()` function at top of file
- Sets `LANGCHAIN_PROJECT` and `LANGCHAIN_TRACING_V2` environment variables
- Call `setup_langsmith()` in `app/main.py` at startup
- All LangChain calls automatically traced once enabled

**2. Performance Metrics Middleware** → `app/main.py`
- Add HTTP middleware after CORS middleware
- Tracks response time for all API endpoints
- Adds `X-Process-Time` header to responses
- Simple implementation: `time.time()` before/after request

**3. Metrics Endpoint** → `app/api/metrics.py` (new file)
- Create new `APIRouter` for metrics endpoints
- `GET /api/metrics/summary` returns summary statistics
- Uses existing `get_compliance_summary()` from compliance_checker
- Mount router in `app/main.py` via `app.include_router(metrics_router)`

**4. Cache Statistics** → Service files
- Track in `design_loader.py` for CSV cache hits/misses
- Track in `vector_store.py` for embedding cache (when implemented)
- Simple counter variables or logging

**Implementation Priority:**
1. ✅ **Complete**: RAG Technique Validation - BM25-only selected (composite score: 0.422)
   - Evaluation notebook: `evaluation/rag_evaluation.py`
   - Results: BM25-only outperformed hybrid, dense-only, and parent-document
   - Saved to LangSmith dataset and local JSON
2. ✅ **Phase 4 Complete**: Curated Plan Testing - Quantitative evaluation completed
   - **Test Script**: `backend/app/tests/test_curated_plans.py` - Handles multi-page PDFs, ground truth comparison, JSON export
   - **Ground Truth CSVs**: `backend/app/data/floor-plans/example_plan_01a.csv`, `example_plan_01b.csv`, `example_plan_02.csv` (manually created)
   - **Results Documentation**: `backend/app/tests/CURATED_PLAN_TEST_RESULTS.md` (297 lines, comprehensive analysis)
   - **Results JSON**: `backend/app/tests/curated_plan_results/*.json` (per-plan results + summary.json)
   - **Metrics Evaluated**: Recall (45.56%), Precision (55.79%), Area accuracy (65.38%), Type match rate (100%)
   - **Key Findings**: Type classification excellent, recall needs improvement (room splitting, missing small rooms), area accuracy good for matched rooms
3. ✅ **COMPLETE**: VLM Extraction Metrics Framework - Similar to RAGAS pattern (Phase 6)
   - Evaluation framework: `evaluation/vlm_extraction_metrics.py` (8 custom metrics with fuzzy matching)
   - Evaluation script: `evaluation/vlm_evaluation.py` (following RAGAS pattern, model comparison)
   - Golden dataset: `evaluation/data/vlm_golden_dataset.json` (automatically matches floor plans to CSV ground truth)
   - Metrics: area_accuracy, recall, precision, type_match_rate, name_match_rate, semantic_understanding_score, confidence_calibration, composite_score
   - **Model Selection**: Gemini 2.0 Flash selected as best model (composite score: 0.753 vs GPT-4o's 0.743)
   - **Results**: Better recall (69.66% vs 53.85%), faster latency (7.61s vs 13.53s), lower cost, comparable accuracy
   - **Defaults Updated**: All code updated to use Gemini 2.0 Flash as default (`app/core/llm.py`, `app/services/blueprint_extractor.py`)
3. **High**: LangSmith setup (automatic tracing, no code changes needed)
4. **Medium**: Performance middleware (simple, useful for monitoring)
5. **Low**: Metrics endpoint (optional, for presentation/monitoring)
6. **Low**: Cache statistics (optional, for optimization insights)

### RAG Technique Validation (COMPLETE)

**Purpose**: Validate retrieval technique choice for building code questions.

**Reference Pattern**: `internal/lessons/day_5/1-advanced_retrievers.py`
- Shows how to evaluate retrievers with RAGAS
- Provides `evaluate_retriever_with_ragas()` function pattern
- Demonstrates comparison of multiple retrieval techniques
- Uses metrics: context_precision, context_recall, answer_relevancy

**Evaluation Completed**:
1. ✅ Created test dataset (12 building code questions)
   - Used RAGAS TestsetGenerator with knowledge graph from building code PDFs
   - Filtered chunks using measurement-related keywords
   - Saved to `evaluation/data/golden_dataset.csv`
2. ✅ Created evaluation notebook: `evaluation/rag_evaluation.py` (Marimo)
   - Adapted `evaluate_retriever_with_ragas()` from day_5 lesson
   - Composite scoring: 50% relevancy, 20% precision, 20% recall, 10% latency
3. ✅ Evaluated 4 retrieval techniques:
   - Dense-only: `get_retriever(k=5, use_hybrid=False)`
   - BM25-only: `BM25Retriever.from_documents()`
   - Hybrid: `get_retriever(k=5, use_hybrid=True)`
   - Parent-Document: Small-to-big strategy from day_5
4. ✅ Results documented:
   - **Best technique: BM25-only** (composite score: 0.422)
   - Results saved to LangSmith dataset and `evaluation/results/evaluation_results.json`
   - LangSmith integration: Can load results from cloud or local cache

**Key Finding**:
- BM25-only outperformed hybrid retrieval for building code questions
- Building codes benefit more from exact term matching than semantic similarity
- Recommendation: Update `vector_store.py` default to BM25-only (or keep hybrid as option)

**Why this matters**:
- ✅ Validated core technical decision with data-driven evidence
- ✅ Provides metrics for presentation (composite scoring methodology)
- ✅ Identified optimal technique before proceeding with frontend/Phase 5

### Rule Extraction with Project Context

**Status**: ✅ **COMPLETE**

**Implementation**:
- `app/services/rule_extractor.py` - LLM-based rule extraction from PDFs using BM25-only retrieval
- `app/models/domain.py` - `ProjectContext` model for filtering rules by project characteristics
- `app/services/rules_seed.py` - Integrated extraction into `get_all_rules()` with context filtering

**Project Context Model**:
- Fields: building_type, number_of_stories, occupancy, building_classification, requires_accessibility, requires_fire_rated
- Default context: Single-floor residential detached house (matches current MVP project)
- Used in extraction prompts to filter out irrelevant rules

**Filtering Logic**:
- Excludes commercial/industrial rules for residential projects
- Excludes fire exit/stairwell rules for single-story buildings
- Excludes public accessibility rules unless required
- Excludes fire-rated requirements unless specified

**Results**:
- Before filtering: 28 compliance issues from 18 rules (included commercial/multi-story rules)
- After filtering: 3 compliance issues from 10 rules (only residential single-story rules)
- Extracted 6-7 relevant rules (down from 14 without filtering)

**Key Features**:
- Uses BM25-only retrieval (validated best technique, composite score: 0.422)
- Structured output parsing (JSON) with validation and error handling
- ID conflict resolution (renames conflicting rule IDs to avoid duplicates)
- Rule type validation (fixes invalid rule_type assignments)
- Graceful error handling with fallback to seeded rules

## Future Enhancements

### User-Provided API Keys (Post-MVP)

**Goal**: Allow users to use their own OpenAI/Gemini API keys instead of server's API key to eliminate server costs and prevent abuse.

**Implementation Plan**:
1. **Update `ChatRequest` model** (`app/api/chat.py`):
   - Add optional `api_key: Optional[str]` field
   - Add optional `provider: str = "openai"` field (support "openai" or "gemini")

2. **Update `get_llm()` function** (`app/core/llm.py`):
   - Add optional `api_key: Optional[str]` parameter
   - Use provided API key if available, otherwise fall back to environment variable
   - Add Gemini support using `langchain_google_genai.ChatGoogleGenerativeAI`

3. **Update chat endpoint** (`app/api/chat.py`):
   - Pass user-provided API key to `get_llm()` if provided
   - Use user's provider preference (OpenAI or Gemini)

4. **Update frontend** (`app/templates/index.html`):
   - Add optional API key input field (password type)
   - Add provider selector dropdown (OpenAI/Gemini)
   - Include API key and provider in chat request body
   - Add instructions: "Enter your API key to use your own credits (optional)"

5. **Security considerations**:
   - Use HTTPS (Railway provides automatically)
   - Never log API keys in server logs
   - Consider rate limiting even with user keys
   - Option: Make API key required (no server costs) or optional (fallback to server key)

**Benefits**:
- ✅ Eliminates server costs for LLM usage
- ✅ Prevents API key abuse
- ✅ Allows users to choose their preferred provider
- ✅ Scales without server cost concerns

**Dependencies**:
- Add `langchain-google-genai` to `pyproject.toml` for Gemini support
- Update frontend UI to include API key input
- Add user instructions/documentation
