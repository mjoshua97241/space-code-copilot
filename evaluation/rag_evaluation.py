import marimo

__generated_with = "0.18.4"
app = marimo.App(width="medium", auto_download=["ipynb"])


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _():
    import os
    import sys
    from pathlib import Path

    # Add backend to path to import app modules
    backend_path = Path(__file__).parent.parent / "backend"
    sys.path.insert(0, str(backend_path))
    return Path, os


@app.cell
def _(Path, os):
    # Load the OpenAI key from the file
    openai_key_path = Path(__file__).parent / "OpenAI_key.txt"
    if openai_key_path.exists():
        with open(openai_key_path, "r") as file:
            os.environ["OPENAI_API_KEY"] = file.read().strip()
    else:
        # Fallback to .env file
        from dotenv import load_dotenv
        env_path = Path(__file__).parent.parent / "backend" / ".env"
        if env_path.exists():
            load_dotenv(env_path)

    print("✔ OpenAI API key loaded")
    return


@app.cell
def _(Path, os):
    # Set LangSmith
    import nest_asyncio

    # Apply nest_asyncio to handle async issues with Ragas
    nest_asyncio.apply()

    # Set LangSmith API key (required for tracing and cost/latency tracking)
    os.environ["LANGSMITH_TRACING_V2"] = "true"

    # Load the LangSmith key from the file
    langsmith_key_path = Path(__file__).parent / "langsmith-api.txt"
    if langsmith_key_path.exists():
        with open(langsmith_key_path, "r") as langsmith_file:
            os.environ["LANGSMITH_API_KEY"] = langsmith_file.read().strip()
    else:
        # Fallback to environment variable
        if not os.getenv("LANGSMITH_API_KEY"):
            print("⚠ LangSmith API key not found. Tracing will be disabled.")
            os.environ["LANGSMITH_TRACING_V2"] = "false"

    # Enable LangSmith tracing with fixed project name (reuses same project)
    os.environ["LANGCHAIN_PROJECT"] = "Building_Code_Copilot_Evaluation"
    print("✔ LangSmith environment configured.")
    return


@app.cell
def _(os):
    from langsmith import Client
    from ragas.testset import TestsetGenerator
    from ragas.llms import LangchainLLMWrapper
    from ragas.embeddings import LangchainEmbeddingsWrapper

    # Initialize the LangSmith client (optional, only if key is available)
    lang_client = None
    if os.getenv("LANGSMITH_API_KEY"):
        try:
            lang_client = Client(api_key=os.getenv("LANGSMITH_API_KEY"))
            print("✔ LangSmith client initialized")
        except Exception as e:
            print(f"⚠ LangSmith client initialization failed: {e}")
    else:
        print("⚠ LangSmith API key not found. LangSmith integration will be disabled.")
    return (
        LangchainEmbeddingsWrapper,
        LangchainLLMWrapper,
        TestsetGenerator,
        lang_client,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # RAG Technique Evaluation for Building Code Copilot

    This notebook evaluates 4 different RAG retrieval techniques to validate the assumption that **Hybrid Retrieval (BM25 + Dense)** is better than alternatives for building code questions.

    ## Techniques to Compare

    1. **Dense-only** (baseline) - Current dense embeddings only
    2. **BM25-only** - Sparse retrieval only
    3. **Hybrid (BM25 + Dense)** - Current implementation (0.5/0.5 weights)
    4. **Parent-Document Retrieval** - Small-to-big strategy (from day_5 lesson)

    ## Evaluation Questions

    1. Does hybrid outperform dense-only? (validates BM25 addition)
    2. Does hybrid outperform BM25-only? (validates dense addition)
    3. How does hybrid compare to parent-document? (different strategy)
    4. Which technique is best for building code questions overall?

    ## Metrics

    Using RAGAS metrics:
    - `context_precision`: Measures precision of retrieved context
    - `context_recall`: Measures recall of retrieved context
    - `answer_relevancy`: Measures relevancy of retrieved context to query
    """)
    return


@app.cell
def _():
    # Import project services
    from app.services.pdf_ingest import ingest_pdf
    from app.services.vector_store import VectorStore
    from app.core.llm import get_llm

    print("✔ Project services imported")
    return VectorStore, get_llm, ingest_pdf


@app.cell
def _(Path, ingest_pdf):
    # Load building code PDFs
    pdf_dir = Path(__file__).parent.parent / "backend" / "app" / "data"
    pdf_files = list(pdf_dir.glob("*.pdf"))

    if not pdf_files:
        print("⚠ No PDF files found in backend/app/data/")
        print(f"   Searched in: {pdf_dir}")
        pdf_chunks = []
    else:
        print(f"Found {len(pdf_files)} PDF files:")
        for pdf_file in pdf_files:
            print(f"  - {pdf_file.name}")

        # Load and chunk all PDFs
        pdf_chunks = []
        for pdf_path in pdf_files:
            try:
                chunks = ingest_pdf(str(pdf_path))
                pdf_chunks.extend(chunks)
                print(f"  ✓ Loaded {pdf_path.name}: {len(chunks)} chunks")
            except Exception as e:
                print(f"  ✗ Failed to load {pdf_path.name}: {e}")

        print(f"\n✔ Total chunks: {len(pdf_chunks)}")
    return (pdf_chunks,)


@app.cell
def _(pdf_chunks):
    # For evaluation, use a subset to save tokens and time
    # 250 chunks is sufficient to test retrieval quality while saving ~90% of tokens
    EVAL_CHUNK_LIMIT = 250

    if len(pdf_chunks) > EVAL_CHUNK_LIMIT:
        eval_chunks = pdf_chunks[:EVAL_CHUNK_LIMIT]
        print(f"📊 Using {len(eval_chunks)} chunks for evaluation (out of {len(pdf_chunks)} total)")
        print(f"   Token savings: ~{len(pdf_chunks) - len(eval_chunks)} chunks × ~1000 tokens = ~{(len(pdf_chunks) - len(eval_chunks)) * 1000:,} tokens")
    else:
        eval_chunks = pdf_chunks
        print(f"📊 Using all {len(eval_chunks)} chunks for evaluation")
    return (eval_chunks,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 2: Setup LLM and Embeddings for RAGAS

    RAGAS needs LLM and embeddings for evaluation metrics.
    """)
    return


@app.cell
def _(get_llm):
    from langchain_openai import OpenAIEmbeddings

    # Setup LLM for RAG chains and RAGAS
    chat_model = get_llm(provider="openai", model_name="gpt-4o-mini", temperature=0.0)

    # Setup embeddings for RAGAS
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

    print("✔ LLM and embeddings configured")
    return OpenAIEmbeddings, chat_model, embeddings


@app.cell
def _(LangchainEmbeddingsWrapper, LangchainLLMWrapper, chat_model, embeddings):
    # Wrap for RAGAS
    generator_llm = LangchainLLMWrapper(chat_model)
    generator_embeddings = LangchainEmbeddingsWrapper(embeddings)

    print("✔ RAGAS wrappers created")
    return generator_embeddings, generator_llm


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 3: Create RAG Prompt Template

    Standard RAG prompt for building code Q&A.
    """)
    return


@app.cell
def _():
    from langchain_core.prompts import ChatPromptTemplate

    RAG_TEMPLATE = """\
    You are a helpful assistant specializing in building codes and architectural compliance.

    Use the context provided below to answer the question about building codes. Be precise and cite specific sections when possible.

    If you do not know the answer, or are unsure, say you don't know.

    Query:
    {question}

    Context:
    {context}
    """

    rag_prompt = ChatPromptTemplate.from_template(RAG_TEMPLATE)
    print("✔ RAG prompt template created")
    return (rag_prompt,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 4: Create Retrievers for Each Technique

    We'll create 4 retrievers:
    1. Dense-only (from VectorStore with use_hybrid=False)
    2. BM25-only (from langchain_community)
    3. Hybrid (from VectorStore with use_hybrid=True)
    4. Parent-Document (from day_5 pattern)
    """)
    return


@app.cell
def _(VectorStore, eval_chunks):
    # Technique 1: Dense-only retriever
    # Create a separate vector store for dense-only (to avoid conflicts)
    dense_vectorstore = VectorStore(
        collection_name="dense_only_eval",
        use_memory=True
    )
    dense_vectorstore.add_documents(eval_chunks)
    dense_retriever = dense_vectorstore.get_retriever(k=5, use_hybrid=False)

    print("✔ Dense-only retriever created")
    return (dense_retriever,)


@app.cell
def _(eval_chunks):
    # Technique 2: BM25-only retriever
    from langchain_community.retrievers import BM25Retriever

    bm25_retriever = BM25Retriever.from_documents(eval_chunks, k=5)

    print("✔ BM25-only retriever created")
    return (bm25_retriever,)


@app.cell
def _(VectorStore, eval_chunks):
    # Technique 3: Hybrid retriever (BM25 + Dense)
    hybrid_vectorstore = VectorStore(
        collection_name="hybrid_eval",
        use_memory=True
    )
    hybrid_vectorstore.add_documents(eval_chunks)
    hybrid_retriever = hybrid_vectorstore.get_retriever(k=5, use_hybrid=True)

    print("✔ Hybrid retriever created")
    return (hybrid_retriever,)


@app.cell
def _(OpenAIEmbeddings, eval_chunks):
    # Technique 4: Parent-Document Retriever
    from langchain.retrievers import ParentDocumentRetriever
    from langchain.storage import InMemoryStore
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from qdrant_client import QdrantClient, models
    from langchain_qdrant import QdrantVectorStore

    # Parent documents (use evaluation chunks as parents)
    parent_docs = eval_chunks

    # Child splitter (smaller chunks for search)
    child_splitter = RecursiveCharacterTextSplitter(chunk_size=750)

    # Create separate vectorstore for parent-document
    parent_client = QdrantClient(location=":memory:")
    parent_client.create_collection(
        collection_name="parent_document_eval",
        vectors_config=models.VectorParams(
            size=1536,  # OpenAI text-embedding-3-small
            distance=models.Distance.COSINE
        )
    )

    parent_vectorstore = QdrantVectorStore(
        collection_name="parent_document_eval",
        embedding=OpenAIEmbeddings(model="text-embedding-3-small"),
        client=parent_client
    )

    # Create docstore for parents
    store = InMemoryStore()

    # Create parent-document retriever
    parent_document_retriever = ParentDocumentRetriever(
        vectorstore=parent_vectorstore,
        docstore=store,
        child_splitter=child_splitter
    )

    # Add documents
    parent_document_retriever.add_documents(parent_docs, ids=None)

    print("✔ Parent-Document retriever created")
    return (parent_document_retriever,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 5: Create RAG Chains for Each Retriever

    Build RAG chains using LCEL (LangChain Expression Language) pattern from day_5.
    """)
    return


@app.cell
def _(chat_model, dense_retriever, rag_prompt):
    from langchain_core.runnables import RunnablePassthrough
    from operator import itemgetter

    # Technique 1: Dense-only RAG chain
    dense_retrieval_chain = (
        {"context": itemgetter("question") | dense_retriever, "question": itemgetter("question")}
        | RunnablePassthrough.assign(context=itemgetter("context"))
        | {"response": rag_prompt | chat_model, "context": itemgetter("context")}
    )

    print("✔ Dense-only RAG chain created")
    return RunnablePassthrough, dense_retrieval_chain, itemgetter


@app.cell
def _(RunnablePassthrough, bm25_retriever, chat_model, itemgetter, rag_prompt):
    # Technique 2: BM25-only RAG chain
    bm25_retrieval_chain = (
        {"context": itemgetter("question") | bm25_retriever, "question": itemgetter("question")}
        | RunnablePassthrough.assign(context=itemgetter("context"))
        | {"response": rag_prompt | chat_model, "context": itemgetter("context")}
    )

    print("✔ BM25-only RAG chain created")
    return (bm25_retrieval_chain,)


@app.cell
def _(
    RunnablePassthrough,
    chat_model,
    hybrid_retriever,
    itemgetter,
    rag_prompt,
):
    # Technique 3: Hybrid RAG chain
    hybrid_retrieval_chain = (
        {"context": itemgetter("question") | hybrid_retriever, "question": itemgetter("question")}
        | RunnablePassthrough.assign(context=itemgetter("context"))
        | {"response": rag_prompt | chat_model, "context": itemgetter("context")}
    )

    print("✔ Hybrid RAG chain created")
    return (hybrid_retrieval_chain,)


@app.cell
def _(
    RunnablePassthrough,
    chat_model,
    itemgetter,
    parent_document_retriever,
    rag_prompt,
):
    # Technique 4: Parent-Document RAG chain
    parent_document_retrieval_chain = (
        {"context": itemgetter("question") | parent_document_retriever, "question": itemgetter("question")}
        | RunnablePassthrough.assign(context=itemgetter("context"))
        | {"response": rag_prompt | chat_model, "context": itemgetter("context")}
    )

    print("✔ Parent-Document RAG chain created")
    return (parent_document_retrieval_chain,)


@app.cell
def _(
    bm25_retrieval_chain,
    dense_retrieval_chain,
    hybrid_retrieval_chain,
    parent_document_retrieval_chain,
):
    # Store all chains in a dictionary for easy iteration
    retriever_chains = {
        "Dense-Only": dense_retrieval_chain,
        "BM25-Only": bm25_retrieval_chain,
        "Hybrid": hybrid_retrieval_chain,
        "Parent-Document": parent_document_retrieval_chain,
    }

    print("✔ All 4 retriever chains created:")
    for name in retriever_chains.keys():
        print(f"  - {name}")
    return (retriever_chains,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 6: Generate Test Dataset

    We'll use RAGAS TestsetGenerator to create synthetic building code questions, or create a manual test set.
    """)
    return


@app.cell
def _(
    Path,
    TestsetGenerator,
    eval_chunks,
    generator_embeddings,
    generator_llm,
):
    import pandas as pd

    # Path for saving/loading golden dataset
    golden_dataset_path = Path(__file__).parent / "data" / "golden_dataset.csv"
    golden_dataset_path.parent.mkdir(exist_ok=True)

    # Check if golden dataset already exists
    if golden_dataset_path.exists():
        print(f"📂 Loading existing golden dataset from {golden_dataset_path}")
        golden_df = pd.read_csv(golden_dataset_path)
        print(f"✔ Loaded {len(golden_df)} test examples")
    else:
        print("🔨 Generating new golden dataset...")

        # Try to use RAGAS TestsetGenerator with knowledge graph
        try:
            from ragas.testset.synthesizers import SingleHopSpecificQuerySynthesizer
            from ragas.testset.graph import KnowledgeGraph, Node, NodeType
            from ragas.testset.transforms import apply_transforms, default_transforms

            # Filter chunks that likely contain measurements and technical requirements
            # This targets the sections with specific building code measurements
            measurement_keywords = [
                'minimum', 'maximum', 'area', 'width', 'height', 'depth',
                'm²', 'meters', 'mm', 'cm', 'section', 'requirement',
                'bedroom', 'living room', 'door', 'corridor', 'stair',
                'ceiling', 'egress', 'accessibility', 'habitable', 'clear'
            ]

            # Filter chunks containing measurement-related keywords
            chunk_subset = [
                chunk for chunk in eval_chunks 
                if any(keyword.lower() in chunk.page_content.lower() 
                      for keyword in measurement_keywords)
            ]

            # Limit to 50 chunks for knowledge graph generation
            if len(chunk_subset) > 50:
                chunk_subset = chunk_subset[:50]
                print(f"Selected 50 chunks (out of {len([c for c in eval_chunks if any(kw.lower() in c.page_content.lower() for kw in measurement_keywords)])} matching) containing measurement-related content")
            elif len(chunk_subset) < 10:
                # Fallback: use middle chunks if not enough matches
                print(f"⚠ Only found {len(chunk_subset)} chunks with measurement keywords. Using middle chunks as fallback...")
                start_idx = len(eval_chunks) // 3
                chunk_subset = eval_chunks[start_idx:start_idx + 50]
                print(f"   Using chunks {start_idx} to {start_idx + len(chunk_subset)}")
            else:
                print(f"Selected {len(chunk_subset)} chunks containing measurement-related content")

            # Build knowledge graph from chunks
            print("Building knowledge graph...")
            kg = KnowledgeGraph()

            for doc in chunk_subset:
                kg.nodes.append(
                    Node(
                        type=NodeType.DOCUMENT,
                        properties={
                            "page_content": doc.page_content,
                            "document_metadata": doc.metadata
                        }
                    )
                )

            # Apply transformations to build the graph
            print("Applying transformations...")
            transforms = default_transforms(
                documents=chunk_subset,
                llm=generator_llm,
                embedding_model=generator_embeddings
            )
            apply_transforms(kg, transforms)

            # Generate new dataset
            generator = TestsetGenerator(
                llm=generator_llm,
                embedding_model=generator_embeddings,
                knowledge_graph=kg
            )

            # Use ONLY SingleHopSpecificQuerySynthesizer to avoid persona bug
            query_distribution = [
                (SingleHopSpecificQuerySynthesizer(llm=generator_llm), 1.0)
            ]

            # Generate synthetic test dataset (10-15 examples for MVP)
            print("Generating synthetic test dataset...")
            golden_dataset = generator.generate(
                testset_size=12,
                query_distribution=query_distribution
            )

            golden_df = golden_dataset.to_pandas()

            # Save to CSV
            golden_df.to_csv(golden_dataset_path, index=False)
            print(f"""
    ✔ Generated {len(golden_df)} test examples using RAGAS TestsetGenerator.
    ✔ Saved to {golden_dataset_path} for future use.
    \nSample question: {golden_df['user_input'].iloc[0][:100]}...
            """)
        except (ImportError, AttributeError) as e:
            # Fallback: Create manual test dataset
            print("⚠ langchain_experimental not available. Creating manual test dataset...")

            # Manual building code questions for evaluation
            manual_questions = [
                {
                    "user_input": "What is the minimum bedroom area required?",
                    "reference": "The minimum bedroom area is 9.5 square meters according to building codes.",
                    "reference_contexts": ["Minimum habitable room area shall be 9.5 m²"]
                },
                {
                    "user_input": "What is the minimum width for an accessible door?",
                    "reference": "Accessible doors must have a minimum clear width of 815mm.",
                    "reference_contexts": ["Accessible door clear width minimum 815mm"]
                },
                {
                    "user_input": "What is the minimum living room area?",
                    "reference": "The minimum living room area is 13.5 square meters.",
                    "reference_contexts": ["Minimum living room area 13.5 m²"]
                },
                {
                    "user_input": "What is the standard door width requirement?",
                    "reference": "Standard doors must have a minimum width of 760mm.",
                    "reference_contexts": ["Standard door minimum width 760mm"]
                },
                {
                    "user_input": "What are the requirements for corridor width?",
                    "reference": "Corridors must have a minimum width of 1.2 meters for accessibility.",
                    "reference_contexts": ["Corridor minimum width 1.2m for accessibility"]
                },
                {
                    "user_input": "What is the minimum ceiling height for habitable rooms?",
                    "reference": "Minimum ceiling height for habitable rooms is 2.4 meters.",
                    "reference_contexts": ["Minimum ceiling height 2.4m for habitable rooms"]
                },
                {
                    "user_input": "What are the egress requirements for bedrooms?",
                    "reference": "Bedrooms must have at least one egress window or door meeting minimum size requirements.",
                    "reference_contexts": ["Bedroom egress requirements minimum window or door"]
                },
                {
                    "user_input": "What is the minimum area for a bathroom?",
                    "reference": "Minimum bathroom area is typically 1.5 square meters.",
                    "reference_contexts": ["Bathroom minimum area 1.5 m²"]
                },
                {
                    "user_input": "What are the requirements for accessible parking spaces?",
                    "reference": "Accessible parking spaces must be at least 3.6 meters wide with an adjacent access aisle.",
                    "reference_contexts": ["Accessible parking minimum 3.6m width with access aisle"]
                },
                {
                    "user_input": "What is the minimum stair width requirement?",
                    "reference": "Minimum stair width is 900mm for residential buildings.",
                    "reference_contexts": ["Minimum stair width 900mm residential"]
                },
            ]

            golden_df = pd.DataFrame(manual_questions)
            golden_df.to_csv(golden_dataset_path, index=False)
            print(f"""
    ✔ Created manual test dataset with {len(golden_df)} questions.
    ✔ Saved to {golden_dataset_path} for future use.
    \nNote: RAGAS TestsetGenerator failed ({str(e)}). Using manual dataset.
    You can edit the manual questions in this cell to match your building codes.
            """)
    return golden_df, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 7: Setup Evaluation Infrastructure

    Define RAGAS metrics and create evaluation helper function.
    """)
    return


@app.cell
def _():
    from ragas import evaluate
    from ragas.metrics import context_precision, context_recall, answer_relevancy
    from datasets import Dataset
    import time

    # Define retriever-specific RAGAS metrics
    ragas_metrics = [context_precision, context_recall, answer_relevancy]

    print("Retriever-specific metrics loaded:")
    print("* `context_precision`: Measures precision of retrieved context.")
    print("* `context_recall`: Measures recall of retrieved context.")
    print("* `answer_relevancy`: Measures relevancy of retrieved context to query.")
    return Dataset, evaluate, ragas_metrics, time


@app.cell
def _(
    Dataset,
    evaluate,
    generator_embeddings,
    generator_llm,
    ragas_metrics,
    time,
):
    def evaluate_retriever_with_ragas(rag_chain, retriever_name, golden_dataset_df, delay_between_questions=0):
        """
        Evaluate a RAG chain using RAGAS metrics

        Args:
            rag_chain: The RAG chain to evaluate (must return dict with 'response' and 'context' keys)
            retriever_name: Name identifier for the retriever
            golden_dataset_df: DataFrame with golden dataset (columns: user_input, reference, reference_contexts)
            delay_between_questions: Delay in seconds between questions (for rate-limited APIs)

        Returns:
            dict: Contains ragas_results (dict of metric scores), latency (float), and formatted_dataset
        """

        print(f"\n{'='*60}")
        print(f"Evaluation: {retriever_name}")
        print(f"{'='*60}")
        if delay_between_questions > 0:
            print(f"⚠ Rate limiting: {delay_between_questions}s delay between questions")

        questions = golden_dataset_df["user_input"].tolist()
        ground_truths = golden_dataset_df['reference'].tolist()

        answers = []
        contexts_list = []
        latencies = []

        # Run RAG chain for each question
        for idx, question in enumerate(questions):
            start_time = time.time()

            # Invoke chain - expects {"question": ...} and returns dict with "response" and "context"
            result = rag_chain.invoke({"question": question})

            latency = time.time() - start_time
            latencies.append(latency)

            # Extract the answers and contexts
            if isinstance(result["response"], str):
                answer = result["response"]
            else:
                answer = result["response"].content if hasattr(result["response"], 'content') else str(result["response"])

            # Extract contents
            contexts = [doc.page_content if hasattr(doc, 'page_content') else str(doc) for doc in result["context"]]
            contexts_list.append(contexts)
            answers.append(answer)

            # Add delay to respect rate limits (except after last question)
            if delay_between_questions > 0 and idx < len(questions) - 1:
                print(f" Question {idx+1}/{len(questions)} complete. Waiting {delay_between_questions}s...")
                time.sleep(delay_between_questions)

        # Format as HuggingFace Dataset for RAGAS
        formatted_dataset = Dataset.from_dict({
            "question": questions,
            "answer": answers,
            "contexts": contexts_list,
            "ground_truth": ground_truths
        })

        # Run RAGAS evaluation
        print(f"Running RAGAS evaluation...")
        try:
            ragas_results = evaluate(
                dataset=formatted_dataset,
                metrics=ragas_metrics,
                llm=generator_llm,
                embeddings=generator_embeddings
            )
        except (TypeError, AttributeError) as e:
            # Fallback: try without explicit embeddings parameter
            print(f"⚠ First attempt failed, trying alternative configuration...")
            try:
                ragas_results = evaluate(
                    dataset=formatted_dataset,
                    metrics=ragas_metrics,
                    llm=generator_llm
                )
            except Exception as e2:
                # Final fallback: basic evaluation
                print(f"⚠ Using basic evaluation...")
                ragas_results = evaluate(
                    dataset=formatted_dataset,
                    metrics=ragas_metrics
                )
        avg_latency = sum(latencies) / len(latencies) if latencies else 0

        print(f"✔ Evaluation complete for {retriever_name}")
        print(f"   Average latency: {avg_latency:.3f}s")

        return {
            "ragas_results": ragas_results,
            "latency": avg_latency,
            "formatted_dataset": formatted_dataset,
            "latencies": latencies
        }

    print("✔ Helper function created")
    return (evaluate_retriever_with_ragas,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 8: Evaluate All Retrievers

    Run evaluation on all 4 retrievers using the golden dataset.
    """)
    return


@app.cell
def _(
    Path,
    evaluate_retriever_with_ragas,
    golden_df,
    lang_client,
    os,
    retriever_chains,
):
    import json
    from datetime import datetime

    # Path for saving/loading evaluation results
    results_path = Path(__file__).parent / "results" / "evaluation_results.json"
    results_path.parent.mkdir(exist_ok=True)

    # LangSmith dataset name for storing evaluation results
    project_name = os.getenv("LANGCHAIN_PROJECT", "Building_Code_Copilot_Evaluation")
    dataset_name = f"{project_name}_evaluation_results"

    results_summary = None

    # Option 1: Try to load from LangSmith first (if client available)
    if lang_client:
        try:
            print(f"🔍 Checking LangSmith for evaluation results in project '{project_name}'...")

            # Try to find existing dataset with evaluation results
            try:
                datasets = list(lang_client.list_datasets(dataset_name=dataset_name))
                if datasets:
                    print(f"   Found dataset: {dataset_name}")
                    # Try to get the latest dataset
                    dataset = datasets[0]

                    # Fetch examples from the dataset (stored as metadata)
                    examples = list(lang_client.list_examples(dataset_id=dataset.id, limit=100))

                    if examples:
                        # Reconstruct results_summary from LangSmith dataset
                        results_summary = []
                        for example in examples:
                            metadata = example.metadata or {}
                            if metadata.get("type") == "evaluation_result":
                                results_summary.append({
                                    "retriever": metadata.get("retriever", ""),
                                    "context_precision": metadata.get("context_precision", 0),
                                    "context_recall": metadata.get("context_recall", 0),
                                    "answer_relevancy": metadata.get("answer_relevancy", 0),
                                    "avg_latency": metadata.get("avg_latency", 0),
                                    "evaluated_at": metadata.get("evaluated_at", ""),
                                    "source": "langsmith"
                                })

                        if results_summary:
                            print(f"✔ Loaded {len(results_summary)} evaluation results from LangSmith")
                            for result in results_summary:
                                print(f"   - {result['retriever']}: relevancy={result['answer_relevancy']:.3f}")
            except Exception as e:
                # Dataset doesn't exist or can't be accessed
                print(f"   No existing dataset found: {e}")

        except Exception as e:
            print(f"   ⚠ Could not query LangSmith: {e}")

    # Option 2: Try to load from local JSON (fallback)
    if results_summary is None and results_path.exists():
        print(f"\n📂 Loading existing evaluation results from local file: {results_path}")
        with open(results_path, "r") as f:
            results_summary = json.load(f)
        print(f"✔ Loaded results for {len(results_summary)} retrievers:")
        for result in results_summary:
            print(f"   - {result['retriever']}: relevancy={result['answer_relevancy']:.3f}")
        print("\n💡 To re-run evaluation, delete the file and re-run this cell.")

    # Option 3: Run evaluation if no cached results found
    if results_summary is None:
        print("\n🔨 Running evaluation (this may take a while and use API credits)...")
        print("   This will evaluate all 4 retrievers on the golden dataset.")
        results_summary = []

        for retriever_name, rag_chain in retriever_chains.items():
            print(f"\n{'#'*60}")
            print(f"# Evaluating: {retriever_name}")
            print(f"{'#'*60}")

            try:
                # Run evaluation
                eval_result = evaluate_retriever_with_ragas(
                    rag_chain=rag_chain,
                    retriever_name=retriever_name,
                    golden_dataset_df=golden_df,
                    delay_between_questions=0  # No rate limiting needed for OpenAI
                )

                # Extract metrics from RAGAS results
                ragas_scores = eval_result["ragas_results"]

                # Convert EvaluationResult to pandas DataFrame to access metrics
                ragas_df = ragas_scores.to_pandas()

                result_data = {
                    "retriever": retriever_name,
                    "context_precision": ragas_df["context_precision"].mean() if "context_precision" in ragas_df.columns else 0,
                    "context_recall": ragas_df["context_recall"].mean() if "context_recall" in ragas_df.columns else 0,
                    "answer_relevancy": ragas_df["answer_relevancy"].mean() if "answer_relevancy" in ragas_df.columns else 0,
                    "avg_latency": eval_result["latency"],
                    "evaluated_at": datetime.now().isoformat(),
                    "golden_dataset_size": len(golden_df),
                    "source": "new_evaluation"
                }

                results_summary.append(result_data)

            except Exception as e:
                print(f"\n❌ Error evaluating {retriever_name}: {str(e)}")
                import traceback
                traceback.print_exc()
                continue

        # Save results to local JSON
        with open(results_path, "w") as f:
            json.dump(results_summary, f, indent=2)
        print(f"\n✔ Results saved to local file: {results_path}")

        # Save results to LangSmith dataset (if client available)
        if lang_client:
            try:
                print(f"\n💾 Saving results to LangSmith dataset '{dataset_name}'...")

                # Create or get dataset
                try:
                    dataset = lang_client.read_dataset(dataset_name=dataset_name)
                    print(f"   Using existing dataset: {dataset.id}")
                except:
                    # Dataset doesn't exist, create it
                    dataset = lang_client.create_dataset(
                        dataset_name=dataset_name,
                        description="RAG technique evaluation results for building code copilot"
                    )
                    print(f"   Created new dataset: {dataset.id}")

                # Add evaluation results as examples with metadata
                for result in results_summary:
                    lang_client.create_example(
                        dataset_id=dataset.id,
                        inputs={"retriever": result["retriever"]},
                        outputs={"status": "evaluated"},
                        metadata={
                            "type": "evaluation_result",
                            "retriever": result["retriever"],
                            "context_precision": result["context_precision"],
                            "context_recall": result["context_recall"],
                            "answer_relevancy": result["answer_relevancy"],
                            "avg_latency": result["avg_latency"],
                            "evaluated_at": result.get("evaluated_at", datetime.now().isoformat()),
                            "golden_dataset_size": result.get("golden_dataset_size", len(golden_df))
                        }
                    )

                print(f"✔ Saved {len(results_summary)} results to LangSmith dataset")
                print(f"   View at: https://smith.langchain.com/datasets/{dataset.id}")

            except Exception as e:
                print(f"   ⚠ Could not save to LangSmith: {e}")
                print("   Results saved locally only.")

        print(f"\n{'='*60}")
        print(f"✓ Completed evaluation for {len(results_summary)} retrievers")
        print(f"{'='*60}")
    return (results_summary,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 9: Compare Results

    Display comparison table and analysis.
    """)
    return


@app.cell
def _(pd, results_summary):
    # Create comparison DataFrame
    results_df = pd.DataFrame(results_summary)

    # Calculate composite score (weighted combination of multiple metrics)
    # Weights can be adjusted based on priorities:
    # - answer_relevancy: 50% (primary - how relevant are answers)
    # - context_precision: 20% (how precise is retrieved context)
    # - context_recall: 20% (how complete is retrieved context)
    # - latency: 10% penalty (normalized, lower is better)

    # Normalize latency (0-1 scale, lower is better, so we subtract from 1)
    max_latency = results_df['avg_latency'].max()
    min_latency = results_df['avg_latency'].min()
    if max_latency > min_latency:
        # Normalize: 1 = fastest, 0 = slowest
        results_df['latency_score'] = 1 - ((results_df['avg_latency'] - min_latency) / (max_latency - min_latency))
    else:
        # All same latency
        results_df['latency_score'] = 1.0

    # Calculate composite score
    results_df['composite_score'] = (
        0.50 * results_df['answer_relevancy'] +
        0.20 * results_df['context_precision'] +
        0.20 * results_df['context_recall'] +
        0.10 * results_df['latency_score']
    )

    # Sort by composite score (primary ranking)
    results_df = results_df.sort_values("composite_score", ascending=False)

    # Also create a version sorted by answer_relevancy for comparison
    results_df_by_relevancy = results_df.sort_values("answer_relevancy", ascending=False)

    print("\n" + "="*60)
    print("RAG TECHNIQUE COMPARISON RESULTS")
    print("="*60)
    print("\n📊 Metrics Table (sorted by Composite Score):")
    print("\n" + results_df[['retriever', 'answer_relevancy', 'context_precision', 
                              'context_recall', 'avg_latency', 'composite_score']].to_string(index=False))
    print("\n" + "="*60)

    # Show ranking by answer_relevancy for comparison
    print("\n📈 Ranking by Answer Relevancy (single metric):")
    for idx, row in results_df_by_relevancy.iterrows():
        rank = list(results_df_by_relevancy.index).index(idx) + 1
        print(f"  {rank}. {row['retriever']}: {row['answer_relevancy']:.3f}")

    print("\n📊 Ranking by Composite Score (multi-metric):")
    for idx, row in results_df.iterrows():
        rank = list(results_df.index).index(idx) + 1
        print(f"  {rank}. {row['retriever']}: {row['composite_score']:.3f} "
              f"(relevancy: {row['answer_relevancy']:.3f}, precision: {row['context_precision']:.3f}, "
              f"recall: {row['context_recall']:.3f}, latency: {row['avg_latency']:.3f}s)")

    # Find best technique (by composite score)
    best_technique = results_df.iloc[0]
    print(f"\n🏆 Best Technique (Composite Score): {best_technique['retriever']}")
    print(f"   Composite Score: {best_technique['composite_score']:.3f}")
    print(f"   Answer Relevancy: {best_technique['answer_relevancy']:.3f}")
    print(f"   Context Precision: {best_technique['context_precision']:.3f}")
    print(f"   Context Recall: {best_technique['context_recall']:.3f}")
    print(f"   Avg Latency: {best_technique['avg_latency']:.3f}s")

    # Also show best by answer_relevancy if different
    best_by_relevancy = results_df_by_relevancy.iloc[0]
    if best_technique['retriever'] != best_by_relevancy['retriever']:
        print(f"\n📌 Best by Answer Relevancy Only: {best_by_relevancy['retriever']} ({best_by_relevancy['answer_relevancy']:.3f})")
    return (results_df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Step 10: Analysis and Conclusions

    Answer the key evaluation questions:
    1. Does hybrid outperform dense-only?
    2. Does hybrid outperform BM25-only?
    3. How does hybrid compare to parent-document?
    4. Which technique is best overall?
    """)
    return


@app.cell
def _(results_df):
    # Extract metrics for each technique
    dense_only = results_df[results_df["retriever"] == "Dense-Only"].iloc[0] if len(results_df[results_df["retriever"] == "Dense-Only"]) > 0 else None
    bm25_only = results_df[results_df["retriever"] == "BM25-Only"].iloc[0] if len(results_df[results_df["retriever"] == "BM25-Only"]) > 0 else None
    hybrid = results_df[results_df["retriever"] == "Hybrid"].iloc[0] if len(results_df[results_df["retriever"] == "Hybrid"]) > 0 else None
    parent_doc = results_df[results_df["retriever"] == "Parent-Document"].iloc[0] if len(results_df[results_df["retriever"] == "Parent-Document"]) > 0 else None

    print("\n" + "="*60)
    print("ANALYSIS")
    print("="*60)

    if hybrid is not None and dense_only is not None:
        hybrid_vs_dense = "✅ YES" if hybrid["answer_relevancy"] > dense_only["answer_relevancy"] else "❌ NO"
        print(f"\n1. Does hybrid outperform dense-only? {hybrid_vs_dense}")
        print(f"   Hybrid: {hybrid['answer_relevancy']:.3f} vs Dense-only: {dense_only['answer_relevancy']:.3f}")

    if hybrid is not None and bm25_only is not None:
        hybrid_vs_bm25 = "✅ YES" if hybrid["answer_relevancy"] > bm25_only["answer_relevancy"] else "❌ NO"
        print(f"\n2. Does hybrid outperform BM25-only? {hybrid_vs_bm25}")
        print(f"   Hybrid: {hybrid['answer_relevancy']:.3f} vs BM25-only: {bm25_only['answer_relevancy']:.3f}")

    if hybrid is not None and parent_doc is not None:
        hybrid_vs_parent = "✅ BETTER" if hybrid["answer_relevancy"] > parent_doc["answer_relevancy"] else "❌ WORSE"
        print(f"\n3. How does hybrid compare to parent-document? {hybrid_vs_parent}")
        print(f"   Hybrid: {hybrid['answer_relevancy']:.3f} vs Parent-Document: {parent_doc['answer_relevancy']:.3f}")

    if hybrid is not None:
        print(f"\n4. Best technique overall: {results_df.iloc[0]['retriever']}")
        print(f"   Answer Relevancy: {results_df.iloc[0]['answer_relevancy']:.3f}")

    print("\n" + "="*60)
    return


@app.cell
def _(Path, results_df):
    # Save results to CSV
    rag_results_path = Path(__file__).parent / "results" / "rag_evaluation_results.csv"
    rag_results_path.parent.mkdir(exist_ok=True)
    results_df.to_csv(rag_results_path, index=False)
    print(f"✔ Results saved to {rag_results_path}")
    return


if __name__ == "__main__":
    app.run()
