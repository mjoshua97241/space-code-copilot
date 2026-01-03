# MVP Implementation Plan

Detailed 2-week implementation plan for Code-Aware Space Planning Copilot MVP, focusing on feasible features that demonstrate advanced RAG capabilities while maintaining realistic scope.

## Scope Decision: MVP vs. Production-Grade

**Decision**: Focus on MVP features that demonstrate value within 2-week timeline.

**What's IN (MVP):**
- Hybrid retrieval (BM25 + Dense embeddings)
- Basic chunking with metadata (source, page, section)
- Citations in LLM output
- Basic guardrails (prompting-based)
- Deterministic calculators (already implemented)
- Working frontend + deployment

**What's OUT (Post-MVP):**
- Structured hierarchy parsing (jurisdiction → code → edition → chapter → section)
- Cross-encoder re-ranking
- Metadata filters + self-query retrieval
- Multi-hop retrieval with reference expansion
- Conflict/version resolution logic
- Domain-tuned embeddings
- Comprehensive evaluation metrics

---

## Week 1: Core RAG Pipeline

### Phase 1: PDF Ingest + Basic Chunking

**Current Status:**
- ✅ `app/services/pdf_ingest.py` exists with basic functionality:
  - PDF loading with `PyMuPDFLoader`
  - Chunking with `RecursiveCharacterTextSplitter` (1000 chars, 100 overlap)
  - Basic metadata: `source`, `chunk_index`
- ⚠️ Missing enhancements:
  - Page numbers in metadata (PyMuPDFLoader should provide this)
  - Section number extraction (regex for "Section X.X.X" or "Chapter X")

**Tasks:**
1. Enhance `app/services/pdf_ingest.py`:
   - Add page numbers to metadata (from PyMuPDFLoader)
   - Extract section numbers from text (simple regex: "Section X.X.X" or "Chapter X")
   - Store in metadata as `section` field

**Deliverable**: PDF → chunks with enhanced metadata (source, page, chunk_index, section)

**Estimated effort**: 1 day (enhancement only, base functionality exists)

**Dependencies**: None

---

### Phase 2: Hybrid Retrieval (BM25 + Dense)

**Status: ✅ COMPLETE**

**Completed:**
- ✅ `app/services/vector_store.py` updated with BM25-only retrieval (validated best):
  - BM25 retriever setup using `BM25Retriever.from_documents()` from `langchain_community.retrievers`
  - **Default changed to BM25-only** (validated via RAGAS evaluation, composite score: 0.422)
  - Hybrid retriever using `EnsembleRetriever` to combine BM25 + Dense (available as option)
  - Document storage: `self.documents` list stores raw documents for BM25 indexing
  - Updated `get_retriever()` method:
    - Returns `BM25Retriever` by default (BM25-only, validated best)
    - New parameter: `use_bm25_only=True` (default) for explicit BM25-only control
    - Configurable `use_hybrid` parameter (default `False`) for hybrid retrieval
    - Configurable weights: `bm25_weight` and `dense_weight` (default 0.5/0.5) for hybrid
    - Backward compatible: Falls back to dense-only if both `use_bm25_only=False` and `use_hybrid=False`
  - Merges results using Reciprocal Rank Fusion (RRF) via `EnsembleRetriever` (when hybrid enabled)
  - Updated docstrings with evaluation results and rationale
- ✅ Dependencies added:
  - `langchain-community>=0.3.0,<0.4.0` (for `BM25Retriever`)
  - `rank-bm25>=0.2.2,<1.0.0` (required by `BM25Retriever`)
- ✅ Tested and verified:
  - `app/tests/test_vector_store.py` created and working
  - Successfully tested with PDF ingestion (733 chunks from National-Building-Code.pdf)
  - Hybrid retrieval returns merged results from both BM25 and dense retrievers

**Implementation pattern** (from day_13 lesson):
```python
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever

# Setup BM25
bm25_retriever = BM25Retriever.from_documents(docs, k=10)

# Setup dense
dense_retriever = vectorstore.as_retriever(search_kwargs={"k": 10})

# Combine
ensemble_retriever = EnsembleRetriever(
    retrievers=[bm25_retriever, dense_retriever],
    weights=[0.5, 0.5]  # Equal weighting
)
```

**Deliverable**: ✅ BM25-only retrieval (default, validated best), hybrid and dense-only available as options

**Estimated effort**: 2-3 days

**Dependencies**: Phase 1 (PDF ingest)

---

### Phase 3: LLM Wrapper + Basic Chat Endpoint

**Status: ✅ COMPLETE**

**Completed:**
- ✅ `app/api/chat.py` created with full RAG-based chat endpoint:
  - `POST /api/chat` endpoint accepting `ChatRequest` with user query
  - Returns `ChatResponse` with answer and citations
  - Uses BM25-only retriever (`vector_store.get_retriever()`) by default (validated best technique)
  - Singleton pattern for vector store initialization (indexes PDFs on first use)
  - LLM cache setup (memory-based for MVP)
  - Citation extraction from retrieved document metadata
  - Pydantic models: `ChatRequest`, `ChatResponse`, `Citation`
  - Proper error handling (ValueError, generic Exception)
  - Environment variable loading (dotenv) for API keys
  - Prompt template with system instructions for building code Q&A
  - Chain: retriever → context building → prompt → LLM → response
  - Updated to use BM25-only retrieval (validated via RAGAS evaluation)
- ✅ Router mounted in `app/main.py` via `app.include_router(chat_router)`
- ✅ `app/core/llm.py` verified working (no changes needed)
- ⚠️ Optional: `setup_langsmith()` for metrics (deferred to Phase 5 or post-MVP)

**Deliverable**: ✅ Working chat endpoint with RAG and citations

**Dependencies**: ✅ Phase 2 (hybrid retrieval) - Complete

---

## RAG Technique Validation (COMPLETE - Before Phase 4)

**Purpose**: Validate the assumption that hybrid retrieval (BM25 + Dense) is better than dense-only for building code questions.

**Reference**: `internal/lessons/day_5/1-advanced_retrievers.py` - Evaluation patterns with RAGAS

**Current Status:**
- ✅ Evaluation notebook created: `evaluation/rag_evaluation.py`
- ✅ Evaluated 4 techniques: Dense-only, BM25-only, Hybrid (BM25 + Dense), Parent-Document Retrieval
- ✅ **Result: BM25-only selected as best technique** (composite score: 0.422)
- ✅ Results saved to LangSmith dataset and local JSON for future reference

**Tasks Completed:**
1. ✅ Created test dataset for building code questions:
   - Used RAGAS TestsetGenerator with knowledge graph from building code PDFs
   - Generated 12 synthetic questions focused on measurement-related content
   - Filtered chunks using keywords (minimum, maximum, area, width, height, etc.)
   - Saved to `evaluation/data/golden_dataset.csv` for reuse

2. ✅ Created evaluation infrastructure:
   - Evaluation notebook: `evaluation/rag_evaluation.py` (Marimo)
   - Evaluation helper: `evaluate_retriever_with_ragas()` adapted from day_5 lesson
   - RAGAS metrics: context_precision, context_recall, answer_relevancy
   - Composite scoring: 50% relevancy, 20% precision, 20% recall, 10% latency

3. ✅ Evaluated 4 retrieval techniques:
   - Dense-only: `vector_store.get_retriever(k=5, use_hybrid=False)`
   - BM25-only: `BM25Retriever.from_documents()`
   - Hybrid: `vector_store.get_retriever(k=5, use_hybrid=True)`
   - Parent-Document: Small-to-big strategy from day_5 lesson
   - All techniques evaluated on same golden dataset

4. ✅ Results documented:
   - **Best technique: BM25-only** (composite score: 0.422)
   - BM25-only outperformed hybrid, dense-only, and parent-document
   - Results saved to LangSmith dataset and local JSON
   - Evaluation can be reloaded from cache (LangSmith or local file)

**Implementation pattern** (from day_5 lesson):
```python
from ragas import evaluate
from ragas.metrics import context_precision, context_recall, answer_relevancy
from datasets import Dataset

# Create RAG chains for both retrievers
dense_chain = create_rag_chain(vector_store.get_retriever(k=5, use_hybrid=False))
hybrid_chain = create_rag_chain(vector_store.get_retriever(k=5, use_hybrid=True))

# Evaluate both
dense_results = evaluate_retriever_with_ragas(dense_chain, "Dense-Only", test_dataset)
hybrid_results = evaluate_retriever_with_ragas(hybrid_chain, "Hybrid", test_dataset)

# Compare metrics
compare_results(dense_results, hybrid_results)
```

**Deliverable**: ✅ Complete - Evaluation notebook with results showing BM25-only is best technique

**Completed**: 
- Evaluation notebook: `evaluation/rag_evaluation.py`
- Results: BM25-only selected (composite score: 0.422)
- Saved to: `evaluation/results/evaluation_results.json` and LangSmith dataset
- LangSmith integration: Results can be loaded from cloud or local cache

**Key Findings**:
- BM25-only outperformed hybrid retrieval for building code questions
- Composite score: 0.422 (BM25-only) vs lower scores for other techniques
- Building codes benefit from exact term matching (section numbers, citations) over semantic similarity
- Recommendation: Update `vector_store.py` default to BM25-only (or keep hybrid as option)

**Why this matters**: 
- ✅ Validated core technical decision with data-driven evidence
- ✅ Provides metrics for presentation (composite scoring methodology)
- ✅ Identified optimal technique before proceeding with frontend/Phase 5

---

## Week 2: Polish + Demo

### Phase 4: Parent-Child Chunking (Optional, if time permits)

**Tasks:**
1. Update `app/services/pdf_ingest.py`:
   - Implement parent-child chunking:
     - **Child chunks**: Small, clause-sized (150-400 tokens)
     - **Parent chunks**: Larger context (chapter/section wrapper)
   - Store parent-child relationships in metadata

2. Update `app/services/vector_store.py`:
   - Use `ParentDocumentRetriever` from LangChain
   - Retrieve children, then attach parent context automatically

**Deliverable**: Parent-child chunking (improves context quality)

**Estimated effort**: 1-2 days

**Dependencies**: Phase 1 (PDF ingest)

**Note**: This is optional. If running behind schedule, skip this and focus on frontend.

---

### Phase 5: Citations + Guardrails

**Tasks:**
1. Update `app/api/chat.py`:
   - Modify LLM prompt to require citations:
     - "For each claim, cite the source document and section number"
     - "Format citations as: [Source: Section X.X.X, Page Y]"
   - Extract citations from LLM response (regex or structured output)
   - Return citations array in response

2. Add basic guardrails:
   - System prompt: "Never claim compliance is guaranteed. Always cite sources."
   - Check for uncited claims in output
   - Add disclaimer: "This is informational only, not legal advice"

**Deliverable**: Citations in output + basic guardrails

**Estimated effort**: 1 day

**Dependencies**: Phase 3 (chat endpoint)

---

### Phase 6: Frontend Implementation

**Tasks:**
1. Create `app/templates/index.html`:
   - Layout: Left (plan viewer), Bottom (issues list), Right (chat panel)
   - Plan viewer: Display `plan.png` image
   - Issues list: Fetch `/api/issues` on page load, render list
   - Chat panel: Form to submit queries, display responses with citations

2. Create/update `app/static/styles.css`:
   - Basic styling for layout (flex/grid)
   - Highlight states for selected issues
   - Chat message styling

3. Add JavaScript (inline or separate file):
   - `fetch('/api/issues')` → render issues
   - `fetch('/api/chat', {method: 'POST', ...})` → render response
   - Basic interactivity (issue selection, chat submission)

**Deliverable**: Working frontend UI

**Estimated effort**: 2 days

**Dependencies**: Phase 3 (chat endpoint), Phase 5 (citations)

---

### Phase 7: Testing + Deployment + Presentation Prep

**Tasks:**
1. Testing:
   - Test PDF ingest with sample building code PDF
   - Test hybrid retrieval (verify BM25 and dense both work)
   - Test chat endpoint with sample queries
   - Test frontend end-to-end

2. Deployment:
   - Create deployment files (see `memory-bank/deployment.md`)
   - Deploy to Railway.app or test locally
   - Verify all endpoints work

3. Presentation prep:
   - Prepare demo data (CSV files, PDF)
   - Create architecture diagram
   - Practice demo flow (7 minutes)
   - Prepare Q&A answers

**Deliverable**: Deployed, tested, ready for demo

**Estimated effort**: 1 day

**Dependencies**: All previous phases

---

## Implementation Order Summary

**Week 1:**
1. Phase 1: PDF Ingest + Basic Chunking (1-2 days)
2. Phase 2: Hybrid Retrieval (2-3 days)
3. Phase 3: LLM Wrapper + Chat Endpoint (1 day)

**Week 2:**
4. Phase 4: Parent-Child Chunking (optional, 1-2 days) OR skip if behind
5. Phase 5: Citations + Guardrails (1 day)
6. Phase 6: Frontend Implementation (2 days)
7. Phase 7: Testing + Deployment + Presentation Prep (1 day)

**Total estimated effort**: 8-11 days (with buffer for Phase 4)

---

## Key Dependencies

```
Phase 1 (PDF Ingest)
    ↓
Phase 2 (Hybrid Retrieval)
    ↓
Phase 3 (Chat Endpoint)
    ↓
Phase 5 (Citations) ──┐
    ↓                 │
Phase 6 (Frontend) ←──┘
    ↓
Phase 7 (Testing/Deploy)

Phase 4 (Parent-Child) is optional and can run in parallel with Phase 5-6
```

---

## Critical Success Factors

1. **Start with working baseline**: Get naive RAG working first, then add hybrid
2. **Test incrementally**: Test each phase before moving to next
3. **Skip Phase 4 if needed**: Parent-child chunking is nice-to-have, not critical
4. **Focus on demo**: Frontend must work for demo, even if basic
5. **Have backup plan**: If hybrid retrieval is complex, fall back to dense-only for demo

---

## Post-MVP Enhancements (Future Work)

These features are valuable but deferred to post-demo:

1. **Structured hierarchy parsing**: Parse PDFs into jurisdiction → code → edition → chapter → section
2. **Cross-encoder re-ranking**: Improve precision after hybrid retrieval
3. **Metadata filters**: Filter by jurisdiction, edition, occupancy type
4. **Multi-hop retrieval**: Follow citations and references automatically
5. **Conflict resolution**: Handle conflicting clauses intelligently
6. **Domain-tuned embeddings**: Fine-tune embeddings on building code terminology
7. **Comprehensive evaluation**: Build test dataset and evaluation metrics

---

## Notes

- **Hybrid retrieval is the key differentiator**: This shows advanced RAG beyond naive similarity search
- **Citations are critical**: Without citations, building code answers are not trustworthy
- **Frontend must work**: Even if basic, demo needs visual interface
- **Deployment is required**: Demo needs live URL or local setup that works

---

## Risk Mitigation

**Risk**: Hybrid retrieval implementation is complex
- **Mitigation**: Start with LangChain's `EnsembleRetriever` (simpler), fall back to dense-only if needed

**Risk**: PDF parsing doesn't extract good metadata
- **Mitigation**: Use simple regex for section numbers, accept basic metadata for MVP

**Risk**: Frontend takes too long
- **Mitigation**: Use minimal HTML/CSS/JS, focus on functionality over polish

**Risk**: Citations extraction is unreliable
- **Mitigation**: Use structured output (Pydantic) or simple regex, accept basic citation format

**Risk**: Running behind schedule
- **Mitigation**: Skip Phase 4 (parent-child), prioritize working end-to-end flow

