import marimo

__generated_with = "0.18.1"
app = marimo.App(width="medium", auto_download=["ipynb"])


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import os
    import getpass
    return (os,)


@app.cell
def _(os):
    # Load the OpenAI key from the file
    with open("evaluation/OpenAI_key.txt", "r") as file:
        os.environ["OPENAI_API_KEY"] = file.read().strip()
    return


@app.cell
def _(os):
    #  Set LangSmith
    import nest_asyncio

    # Apply nest_asyncio to handle async issues with Ragas
    nest_asyncio.apply()

    # Set LangSmith API key (required for tracing and cost/latency tracking)
    os.environ["LANGSMITH_TRACING_V2"] = "true"

    # Load the LangSmith key from the file
    with open("evaluation/langsmith-api.txt", "r") as langsmith_file:
        os.environ["LANGSMITH_API_KEY"] = langsmith_file.read().strip()

    # Enable LangSmith tracing with fixed project name (reuses same project)
    os.environ["LANGCHAIN_PROJECT"] = "PSI_Demo_Project"
    print("✔ LangSmith environment configured.")
    return


@app.cell
def _(os):
    from langsmith import Client
    from ragas.testset import TestsetGenerator
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    # Initialize the LangSmith client
    lang_client = Client(api_key=os.environ.get("LANGCHAIN_API_KEY"))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Updating the plan to use Parent-Document Retrieval instead of weighted hybrid. This adds a different technique to compare.

    ## Updated techniques to compare

    1. Dense-only (baseline) — current dense embeddings only
    2. BM25-only — sparse retrieval only
    3. Hybrid (BM25 + Dense) — current implementation (0.5/0.5 weights)
    4. Parent-Document Retrieval — small-to-big strategy (from day_5 lesson)

    ## Why Parent-Document Retrieval

    From day_5 lesson:
    - Searches small chunks (better precision)
    - Returns larger parent documents (more context)
    - Useful for building codes where context matters
    - Different approach from hybrid retrieval

    ## Updated implementation approach

    ```python
    # evaluation/rag_evaluation.py (Marimo notebook structure)

    # 1. Setup
    - Load environment variables
    - Setup LangSmith (optional)
    - Setup RAGAS

    # 2. Load building code PDFs
    - Use backend/app/data/*.pdf
    - Chunk using existing pattern

    # 3. Create retrievers for each technique:

    # Technique 1: Dense-only
    dense_retriever = vector_store.get_retriever(k=5, use_hybrid=False)

    # Technique 2: BM25-only
    from langchain_community.retrievers import BM25Retriever
    bm25_retriever = BM25Retriever.from_documents(pdf_chunks, k=5)

    # Technique 3: Hybrid (BM25 + Dense)
    hybrid_retriever = vector_store.get_retriever(k=5, use_hybrid=True)

    # Technique 4: Parent-Document Retrieval
    from langchain.retrievers import ParentDocumentRetriever
    from langchain.storage import InMemoryStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Setup parent-document retriever (from day_5 pattern)
    parent_docs = pdf_chunks  # Or use original PDF pages as parents
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=750)

    # Create separate vectorstore for parent-document
    parent_vectorstore = QdrantVectorStore(...)  # New vectorstore
    store = InMemoryStore()

    parent_document_retriever = ParentDocumentRetriever(
        vectorstore=parent_vectorstore,
        docstore=store,
        child_splitter=child_splitter
    )
    parent_document_retriever.add_documents(parent_docs)

    # 4. Create RAG chains (same pattern as day_5)
    retriever_chains = {
        "Dense-Only": create_rag_chain(dense_retriever),
        "BM25-Only": create_rag_chain(bm25_retriever),
        "Hybrid": create_rag_chain(hybrid_retriever),
        "Parent-Document": create_rag_chain(parent_document_retriever)
    }

    # 5. Generate test dataset
    - Use RAGAS TestsetGenerator (from day_5)
    - Or manual building code questions

    # 6. Evaluate all techniques
    - Use evaluate_retriever_with_ragas() pattern from day_5
    - Compare metrics side-by-side

    # 7. Analysis
    - Which is best for building codes?
    - Does hybrid validate the assumption?
    - How does parent-document compare?
    ```

    ## Parent-Document Retrieval implementation details

    From day_5 lesson (lines 612-744):

    ```python
    # Pattern from day_5:
    from langchain.retrievers import ParentDocumentRetriever
    from langchain.storage import InMemoryStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    # Parent documents (larger chunks or original pages)
    parent_docs = pdf_chunks  # Or use original PDF pages

    # Child splitter (smaller chunks for search)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=750)

    # Create vectorstore for children
    parent_vectorstore = QdrantVectorStore(...)

    # Create docstore for parents
    store = InMemoryStore()

    # Create retriever
    parent_document_retriever = ParentDocumentRetriever(
        vectorstore=parent_vectorstore,
        docstore=store,
        child_splitter=child_splitter
    )

    # Add documents
    parent_document_retriever.add_documents(parent_docs)
    ```

    ## Comparison rationale

    - Dense-only: Baseline semantic search
    - BM25-only: Baseline exact term matching
    - Hybrid: Combines both (current assumption)
    - Parent-Document: Different strategy (small search, big context)

    This tests whether hybrid is better than alternatives, including a context-focused approach.

    ## Updated evaluation questions

    1. Does hybrid outperform dense-only? (validates BM25 addition)
    2. Does hybrid outperform BM25-only? (validates dense addition)
    3. How does hybrid compare to parent-document? (different strategy)
    4. Which technique is best for building code questions overall?

    Should I provide the complete marimo notebook code adapted for your building code context with these 4 techniques?
    """)
    return


if __name__ == "__main__":
    app.run()
