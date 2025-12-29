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

**Tasks:**
1. Complete `app/services/pdf_ingest.py`:
   - Load PDF using `PyMuPDFLoader`
   - Chunk with `RecursiveCharacterTextSplitter` (1000 chars, 100 overlap)
   - Add basic metadata: `source`, `page`, `chunk_index`
   - Extract section numbers from text (simple regex: "Section X.X.X" or "Chapter X")

**Deliverable**: PDF → chunks with metadata

**Estimated effort**: 1-2 days

**Dependencies**: None

---

### Phase 2: Hybrid Retrieval (BM25 + Dense)

**Tasks:**
1. Update `app/services/vector_store.py`:
   - Keep existing `VectorStore` class with dense embeddings
   - Add `BM25Retriever` setup (from `langchain_community.retrievers`)
   - Create `HybridRetriever` class that combines both:
     - Run BM25 search (top K results)
     - Run dense search (top K results)
     - Merge results using Reciprocal Rank Fusion (RRF) or weighted scoring
     - Deduplicate by document ID
     - Return top N final results

2. Update `get_retriever()` method:
   - Return hybrid retriever instead of dense-only
   - Support configurable K values for each retriever

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

**Deliverable**: Hybrid retrieval working (BM25 + Dense)

**Estimated effort**: 2-3 days

**Dependencies**: Phase 1 (PDF ingest)

---

### Phase 3: LLM Wrapper + Basic Chat Endpoint

**Tasks:**
1. Complete `app/core/llm.py`:
   - `get_llm()` function (already exists, verify it works)
   - `setup_llm_cache()` function (already exists)
   - Add `setup_langsmith()` for metrics (optional but recommended)

2. Create `app/api/chat.py`:
   - `POST /api/chat` endpoint
   - Accepts: `{"query": "user question"}`
   - Uses hybrid retriever to get context
   - Passes context + query to LLM
   - Returns: `{"answer": "...", "citations": [...]}`

3. Mount chat router in `app/main.py`

**Deliverable**: Working chat endpoint with RAG

**Estimated effort**: 1 day

**Dependencies**: Phase 2 (hybrid retrieval)

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

