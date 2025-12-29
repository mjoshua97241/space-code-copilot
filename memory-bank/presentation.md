# Presentation Guide

Reference document for preparing the bootcamp demo presentation covering Problem, Solution, Architecture, Metrics, and Demo.

## 1. Problem

### Key Points to Cover

**Primary Problem:**
- Architects manually check room areas, door widths, and corridor widths against building codes
- This process is slow, error-prone, and time-consuming

**Key Pain Points:**

1. **Multiple jurisdictions, multiple codes**
   - Architects work across different locations (Philippines, US, etc.)
   - Each location has its own building code (National Building Code of Philippines, IBC, local codes)
   - Must read and familiarize with many different code documents
   - Time-consuming to switch between different code contexts

2. **Code complexity**
   - Building codes are dense, technical documents (hundreds of pages)
   - Finding relevant requirements for specific design elements requires extensive reading
   - Cross-referencing between sections is tedious

3. **Manual checking**
   - Verifying compliance involves manually comparing design values against code requirements
   - Slow process: read code → find relevant section → compare values → document violations
   - Error-prone: easy to miss requirements or misinterpret rules

**Real-world impact:**
- Architects spend hours reading code documents instead of designing
- Compliance issues discovered late in the design process (expensive to fix)
- Risk of missing requirements when working with unfamiliar codes

### Visuals to Consider
- Screenshot of a dense building code PDF (showing complexity)
- Diagram showing multiple jurisdictions → multiple codes → manual checking
- Time comparison: manual checking vs. automated checking

---

## 2. Solution

### Key Points to Cover

**Code-Aware Space Planning Copilot:**
- Automated compliance checking for early-stage space planning
- Uses LLM/RAG to understand building codes without manual reading
- Provides instant feedback on design violations

**How LLM/RAG Solves the Problem:**

1. **RAG (Retrieval-Augmented Generation)**
   - Ingests multiple building code PDFs automatically
   - Answers questions about requirements without reading entire documents
   - Supports multiple code documents simultaneously (multi-jurisdiction)

2. **Rule extraction**
   - LLM automatically extracts structured rules from code PDFs
   - Converts unstructured text into measurable requirements (e.g., "minimum bedroom area: 9.5 m²")
   - Reduces need to manually identify and codify requirements

3. **Automated compliance checking**
   - Compares design values (from CSV) against extracted rules
   - Generates structured issue reports with code references
   - Instant feedback on violations

**MVP Features:**
- CSV-based design input (rooms, doors)
- Automated compliance checking against rules
- Issue reporting with code references
- Chat interface for code questions (RAG-powered)
- Multi-code support (can handle multiple building code PDFs)

### Visuals to Consider
- Architecture diagram showing: CSV → Compliance Checker → Issues
- RAG flow: PDF → Embeddings → Vector Store → LLM → Answer
- Before/after comparison: manual checking vs. automated checking

---

## 3. Architecture

### Key Points to Cover

**Tech Stack:**
- **Backend**: Python 3.11+, FastAPI, uvicorn
- **AI/LLM**: LangChain + LangGraph, OpenAI/Gemini/Claude (configurable)
- **Vector Store**: Qdrant (in-memory for MVP, persistent for production)
- **Frontend**: Plain HTML/CSS/JS (no build toolchain, served by FastAPI)

**System Architecture:**

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (HTML/JS)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ Plan Viewer  │  │ Issues List  │  │ Chat Panel   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         │ HTTP
                         ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ /api/issues  │  │  /api/chat   │  │   /health    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ CSV Loaders  │    │ Compliance   │    │ RAG Pipeline │
│ (cached)     │    │ Checker      │    │ (Vector DB)  │
└──────────────┘    └──────────────┘    └──────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Room/Door    │    │ Rule Models  │    │ LLM (OpenAI) │
│ Models       │    │ (Seeded +    │    │ + Embeddings │
│              │    │  Extracted)  │    │              │
└──────────────┘    └──────────────┘    └──────────────┘
```

**Component Breakdown:**

1. **Data Layer**
   - CSV files: `rooms.csv`, `doors.csv` (design input)
   - PDF files: Building code documents (e.g., `code_sample.pdf`)
   - Cached CSV parsing (`@lru_cache` for performance)

2. **Business Logic Layer**
   - `design_loader.py`: Loads and validates CSV data
   - `compliance_checker.py`: Checks design against rules
   - `rules_seed.py`: Hardcoded rules (MVP baseline)
   - `rule_extractor.py`: LLM-based rule extraction from PDFs
   - `pdf_ingest.py`: PDF loading and chunking
   - `vector_store.py`: Embeddings and vector search

3. **API Layer**
   - `/api/issues`: Returns compliance issues
   - `/api/chat`: RAG-powered chat for code questions
   - `/health`: Health check endpoint

4. **AI/LLM Layer**
   - `app/core/llm.py`: LLM client abstraction (OpenAI/Gemini/Claude)
   - RAG pipeline: PDF → chunks → embeddings → vector store → retrieval → LLM
   - Caching: `CacheBackedEmbeddings` for embeddings, `setup_llm_cache()` for LLM responses

**Key Design Decisions:**

- **Deterministic compliance checking**: Simple numeric rules (area, width) use Python logic, not LLM
- **LLM for complex tasks**: Rule extraction, RAG queries, issue summarization
- **Multi-code support**: Vector store can index multiple PDFs simultaneously
- **Caching strategy**: Different caching for CSV (lru_cache), embeddings (file-based), LLM (memory/SQLite)

### Visuals to Consider
- System architecture diagram (above)
- Component interaction flow
- Data flow: CSV → Models → Compliance Check → Issues
- RAG flow: PDF → Chunks → Embeddings → Vector Store → Retrieval → LLM

---

## 4. Metrics

### Metrics Implementation (Based on Lessons)

**Reference patterns from `internal/lessons/`:**
- **LangSmith** (day_12): Tracing and monitoring for LLM calls
- **RAGAS** (day_13): Evaluation framework for RAG systems

### Metrics to Track

#### 1. System Performance Metrics

**API Response Times:**
- `/api/issues` endpoint latency
- `/api/chat` endpoint latency
- Vector search retrieval time
- LLM response time

**Implementation:**
```python
# Add to FastAPI endpoints
import time
from fastapi import Request

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```
**Cache Hit Rates:**
- CSV cache hit rate (from `@lru_cache`)
- Embedding cache hit rate (from `CacheBackedEmbeddings`)
- LLM response cache hit rate (from `setup_llm_cache()`)

**Implementation:**
- Track cache statistics in service layer
- Log cache hits/misses for analysis

#### 2. LLM/RAG Metrics (LangSmith Integration)

**Pattern from day_12 lesson:**
```python
# In app/core/llm.py or app/main.py
import os
import uuid

# Set up LangSmith for tracing and monitoring
os.environ["LANGCHAIN_PROJECT"] = f"Code-Aware-Space-Planning-{uuid.uuid4().hex[0:8]}"
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Optional: Set up LangSmith API Key
if os.getenv("LANGCHAIN_API_KEY"):
    print("✓ LangSmith tracing enabled")
else:
    os.environ["LANGCHAIN_TRACING_V2"] = "false"
    print("⚠ LangSmith tracing disabled")
```

**Metrics to track via LangSmith:**
- LLM token usage (input/output tokens)
- LLM latency per call
- Embedding API calls and latency
- RAG retrieval quality (relevance scores)
- Cost tracking (per API call)

**Implementation:**
- Add LangSmith setup to `app/core/llm.py`
- All LangChain calls automatically traced
- View traces in LangSmith dashboard

#### 3. RAG Quality Metrics (RAGAS Evaluation)

**Pattern from day_13 lesson:**
- Use RAGAS framework to evaluate RAG system quality
- Metrics: faithfulness, answer relevancy, context precision, context recall

**Implementation (for evaluation/testing):**
```python
# Add to backend/pyproject.toml
# ragas>=0.1.0

# Create app/services/rag_evaluator.py (optional, for testing)
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy, context_precision

# Evaluate RAG responses on test dataset
results = evaluate(
    dataset=test_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision]
)
```**Metrics to track:**
- **Faithfulness**: How grounded is the answer in the retrieved context?
- **Answer Relevancy**: How relevant is the answer to the question?
- **Context Precision**: How precise is the retrieved context?
- **Context Recall**: How much relevant context was retrieved?

#### 4. Business/Functional Metrics

**Compliance Checking:**
- Number of issues detected per design
- Issue distribution by type (room area, door width, etc.)
- Issue severity breakdown
- False positive rate (if manually validated)

**Rule Extraction:**
- Number of rules extracted per PDF
- Rule extraction accuracy (manual validation)
- Rules by type (area_min, width_min, text)

**User Engagement:**
- Number of chat queries per session
- Average query length
- Most common query types

#### 5. Cost Metrics

**LLM API Costs:**
- Total tokens used (input + output)
- Cost per API call
- Cost per compliance check
- Cost per chat query
- Monthly cost projection

**Implementation:**
- Track via LangSmith (automatic)
- Or manually log token usage in service layer

### Metrics Dashboard (Optional)

**For presentation, show:**
- Simple metrics endpoint: `GET /api/metrics`
- Or use LangSmith dashboard (if API key configured)
- Or create simple HTML dashboard showing key metrics

**Example metrics endpoint:**
```python
# In app/api/metrics.py
from fastapi import APIRouter
from app.services.compliance_checker import get_compliance_summary

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

@router.get("/summary")
def get_metrics_summary():
    """Return summary metrics for presentation."""
    issues = load_and_check_compliance()  # Your existing function
    summary = get_compliance_summary(issues)
    
    return {
        "total_issues": len(issues),
        "issues_by_type": summary["by_type"],
        "issues_by_severity": summary["by_severity"],
        "cache_stats": get_cache_stats(),  # Implement this
        "llm_calls_today": get_llm_call_count(),  # Implement this
    }
```

### Presentation Metrics to Highlight

**For bootcamp demo, focus on:**
1. **Speed**: Compliance check completes in <1 second (vs. hours manually)
2. **Accuracy**: Correctly identifies violations (show test results)
3. **Cost efficiency**: Caching reduces API calls (show cache hit rates)
4. **Scalability**: Can handle multiple code documents simultaneously

---

## 5. Demo Presentation

### Demo Flow (7 minutes total)

**1. Problem (1 min)**
- Show a dense building code PDF
- "Architects must read hundreds of pages like this"
- "Different codes for different jurisdictions"
- "Manual checking is slow and error-prone"

**2. Solution Overview (1 min)**
- Show CSV input files (rooms.csv, doors.csv)
- "We input design data as simple CSVs"
- "The system automatically checks compliance using LLM/RAG"
- Highlight: Automated rule extraction + compliance checking

**3. Architecture (1.5 min)**
- Show system architecture diagram
- Explain key components: CSV loaders, compliance checker, RAG pipeline
- Highlight caching strategy and multi-code support

**4. Metrics (1 min)**
- Show LangSmith dashboard (if available) or metrics endpoint
- Response times: "Compliance check in <1 second"
- Cache hit rates: "80% cache hit rate reduces API costs"
- Token usage and cost tracking

**5. Live Demo (2.5 min)**
- Show deployed app (Railway URL or local)
- Load design data and show `/api/issues` endpoint response
- Highlight violations: "Door D001 is 600mm, but code requires 800mm for accessibility"
- Show frontend displaying issues (if implemented)
- Quick RAG/Chat demo (if implemented): "What is the minimum bedroom area requirement?"
- Key takeaway: "Automated compliance checking saves hours of manual work"

**Q&A (3 minutes)**
- Be prepared for questions on:
  - Technical implementation details
  - LLM accuracy and reliability
  - Cost and scalability
  - Future enhancements

### Demo Checklist

**Before demo:**
- [ ] App deployed and accessible (Railway or local)
- [ ] Sample data loaded (rooms.csv, doors.csv)
- [ ] Building code PDFs indexed in vector store
- [ ] Test compliance check returns expected issues
- [ ] Chat endpoint working with RAG
- [ ] LangSmith tracing enabled (optional)
- [ ] Metrics endpoint working (optional)

**During demo:**
- [ ] Show problem (dense PDF)
- [ ] Show solution (CSV input → issues output)
- [ ] Demonstrate compliance checking
- [ ] Demonstrate RAG chat
- [ ] Show architecture diagram
- [ ] Show metrics (if available)

**Backup plan:**
- If live demo fails, have screenshots/video ready
- Have test results pre-computed
- Have metrics data pre-calculated

### Visual Aids

**Slides to prepare:**
1. Title slide: "Code-Aware Space Planning Copilot"
2. Problem slide: Multiple jurisdictions, dense codes, manual checking
3. Solution slide: Automated compliance + RAG chat
4. Architecture diagram
5. Metrics dashboard/summary
6. Demo screenshots
7. Key takeaways

**Screenshots to capture:**
- Building code PDF (showing complexity)
- CSV input files
- Issues API response
- Frontend showing issues
- Chat interface with RAG response
- LangSmith dashboard (if available)
- Metrics endpoint response

---

## Presentation Structure Summary

**Total time: 7 minutes presentation + 3 minutes Q&A = 10 minutes**

1. **Problem** (1 min)
   - Multiple jurisdictions, multiple codes
   - Code complexity
   - Manual checking pain points

2. **Solution** (1 min)
   - Code-Aware Space Planning Copilot overview
   - How LLM/RAG solves the problem
   - MVP features

3. **Architecture** (1.5 min)
   - Tech stack
   - System architecture diagram
   - Component breakdown
   - Key design decisions

4. **Metrics** (1 min)
   - System performance metrics
   - LLM/RAG metrics (LangSmith)
   - RAG quality metrics (RAGAS)
   - Business metrics
   - Cost metrics

5. **Demo** (2.5 min)
   - Live demonstration
   - Compliance checking
   - RAG chat (if implemented)
   - Metrics overview

**Q&A: 3 minutes**

---

## Next Steps

1. **Implement metrics tracking:**
   - Add LangSmith setup to `app/core/llm.py`
   - Add metrics endpoint (`app/api/metrics.py`)
   - Add cache statistics tracking

2. **Prepare demo data:**
   - Ensure sample CSV files are ready
   - Index building code PDFs in vector store
   - Pre-compute test results

3. **Create visual aids:**
   - Architecture diagram
   - Problem/solution slides
   - Metrics dashboard screenshots

4. **Practice demo flow:**
   - Rehearse each section
   - Time each segment
   - Prepare backup screenshots/video