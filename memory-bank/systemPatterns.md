# System Patterns

Backend patterns:

- FastAPI app in `app/main.py`:
  - Use `Path(__file__).parent` for absolute paths to static/templates directories.
  - Mount static files: `app.mount("/static", StaticFiles(directory=...))`
  - Setup templates: `Jinja2Templates(directory=...)`
- API routes in app/api/\*.py, mounted in app/main.py via include_router.
- Services in app/services/\*.py encapsulate:
  - design_loader (CSV → Room/Door models)
  - pdf_ingest (PDF → chunks)
  - vector_store (embedding + Qdrant search)
  - compliance_checker (rules + design → issues)
  - rule_extractor (LLM-based rule extraction from PDFs; MVP core feature)
- LLM client abstraction in app/core/llm.py to swap OpenAI/Gemini/Claude.

AI patterns:

- Use RAG for building-code questions:
  - user query → embed → vector search over code chunks → pass snippets + question to chat model.
  - Supports multiple code documents simultaneously (multi-jurisdiction support).
  - Architects can query across different building codes without switching contexts.
- Use deterministic Python for simple numeric compliance (area, widths).
- Use LLM for:
  - summarizing issues
  - answering questions via RAG (handles multiple code documents)
  - extracting rules from PDFs (MVP core feature) - automatically processes multiple code PDFs

Frontend patterns:

- Single HTML template (`app/templates/index.html`) served by FastAPI via Jinja2Templates.
- Layout structure:
  - Left: plan viewer (`<img src="/static/plan.png">` + overlay `<div>`s positioned absolutely).
  - Bottom: issues list container.
  - Right: chat panel with form and message container.
- JavaScript (inline or minimal separate script):
  - On page load: `fetch('/api/issues')` → render issues list.
  - On issue click: save `element_id`, highlight corresponding overlay in plan viewer.
  - On chat submit: `fetch('/api/chat', {method: 'POST', body: ...})` → render reply.
  - DOM manipulation: create/update elements for issues and messages.
- CSS (`app/static/styles.css`): layout (flex/grid), styling, highlight states.
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
- **File**: `app/services/vector_store.py` (to be implemented)

#### LLM Response Cache (`llm.py`)
- **Purpose**: Cache LLM API responses
- **Strategy**: `setup_llm_cache()` pattern from day_12 lesson
- **Why**: LLM API calls are slow, expensive, and often have identical prompts
- **Implementation**:
  - Uses `InMemoryCache` (dev) or `SQLiteCache` (production)
  - Configured via `setup_llm_cache(cache_type="memory"|"sqlite")`
  - Caches at LangChain global level
- **File**: `app/core/llm.py` (to be implemented)

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
- `app/core/llm.py` - Multi-provider LLM abstraction (OpenAI/Gemini/Claude switching)
- `app/services/rule_extractor.py` - LLM-based extraction patterns (structured output, prompt engineering)
- `app/services/pdf_ingest.py` - PDF chunking patterns (if complex chunking strategies needed)
- LangGraph agent orchestration (if we add agent workflows)

**Decision process:**
1. If it's a standard Python/library pattern → implement directly
2. If it's LLM/AI-specific and complex → check lessons for patterns
3. Use `/use-lesson-pattern` command when explicitly requested
