"""
Vector store service: Embeddings + Qdrant for RAG retrieval with BM25-Only (Validated).

Based on RAGAS evaluation results (composite score: 0.422), BM25-only retrieval
outperformed hybrid (BM25 + Dense), dense-only, and parent-document retrieval for
building code questions.

Adapted from:
- day_12: CacheBackedEmbeddings for embedding caching
- day_9_A2A: QdrantVectorStore setup
- day_13: Hybrid retrieval pattern (BM25 + Dense via EnsembleRetriever)
- day_5: BM25 retrieval evaluation patterns
"""
import hashlib
import os
from pathlib import Path
from typing import List, Optional
from langchain_core.documents import Document
from langchain.embeddings import CacheBackedEmbeddings as LangChainCacheBackedEmbeddings
from langchain.storage import LocalFileStore
from langchain_openai.embeddings import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Hybrid retrieval imports
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever


class CacheBackedEmbeddings:
    """
    Production cache-backed embeddings using OpenAI.
    
    Pattern from day_12-Caching-Guardrails_and_Reasoning/langgraph_agent_lib/caching.py
    """
    
    def __init__(
        self, 
        model: str = "text-embedding-3-small",
        cache_dir: str = "./cache/embeddings",
        batch_size: int = 32
    ):
        """
        Initialize cache-backed embeddings.
        
        Args:
            model: OpenAI embedding model name
            cache_dir: Directory to store embedding cache
            batch_size: Batch size for embedding calls
        """
        self.model = model
        self.cache_dir = cache_dir
        self.batch_size = batch_size
        
        # Create base embeddings
        self.base_embeddings = OpenAIEmbeddings(model=model)
        
        # Create safe namespace from model name
        safe_namespace = hashlib.md5(model.encode()).hexdigest()
        
        # Set up file store and cached embeddings
        os.makedirs(cache_dir, exist_ok=True)
        store = LocalFileStore(cache_dir)
        self.cached_embeddings = LangChainCacheBackedEmbeddings.from_bytes_store(
            self.base_embeddings, 
            store, 
            namespace=safe_namespace,
            batch_size=batch_size
        )
    
    def get_embeddings(self):
        """Get the cached embeddings instance."""
        return self.cached_embeddings


class VectorStore:
    """
    Vector store with caching and BM25-only retrieval (validated via RAGAS evaluation).
    
    **Evaluation Results** (from `evaluation/rag_evaluation.py`):
    - BM25-only: Composite score 0.422 (best) - answer_relevancy: 0.585
    - Hybrid (BM25 + Dense): answer_relevancy: 0.584
    - Dense-only: answer_relevancy: 0.384
    - Parent-Document: answer_relevancy: 0.462
    
    **Default**: BM25-only retrieval (validated as best for building codes)
    - BM25: Exact term matching (section numbers, citations, legal phrases)
    - Building codes benefit more from exact term matching than semantic similarity
    
    **Options**: Hybrid (BM25 + Dense) and dense-only available via `get_retriever()` parameters
    
    Pattern adapted from:
    - day_12: CacheBackedEmbeddings for embedding caching
    - day_9_A2A: QdrantVectorStore setup
    - day_13: Hybrid retrieval via EnsembleRetriever
    - day_5: BM25 retrieval evaluation patterns
    """
    
    def __init__(
        self,
        collection_name: str = "building_codes",
        embedding_model: str = "text-embedding-3-small",
        cache_dir: str = "./cache/embeddings",
        use_memory: bool = True  # Use in-memory Qdrant for MVP
    ):
        """
        Initialize vector store with caching.
        
        Args:
            collection_name: Qdrant collection name
            embedding_model: OpenAI embedding model name
            cache_dir: Directory for embedding cache
            use_memory: If True, use in-memory Qdrant (MVP). If False, use persistent storage.
        """
        self.collection_name = collection_name
        self.embedding_model = embedding_model
        self.cache_dir = cache_dir
        self.use_memory = use_memory
        
        # Store documents for BM25 retrieval (needs raw text, not just embeddings)
        self.documents: List[Document] = []
        
        # Setup caching (day_12 pattern)
        self._setup_embeddings()
        
        # Setup vector store
        self._setup_vectorstore()
    
    def _setup_embeddings(self):
        """Setup cache-backed embeddings (day_12 lesson pattern)."""
        self.cached_embeddings_wrapper = CacheBackedEmbeddings(
            model=self.embedding_model,
            cache_dir=self.cache_dir
        )
        self.embeddings = self.cached_embeddings_wrapper.get_embeddings()
    
    def _setup_vectorstore(self):
        """Setup Qdrant vector store (day_9_A2A pattern)."""
        if self.use_memory:
            # In-memory Qdrant for MVP
            client = QdrantClient(":memory:")
        else:
            # Persistent storage (future)
            client = QdrantClient(path="./qdrant_db")
        
        # Create collection if needed
        try:
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=1536,  # OpenAI text-embedding-3-small size
                    distance=Distance.COSINE
                )
            )
        except Exception:
            # Collection already exists
            pass
        
        # Create vector store
        self.vectorstore = QdrantVectorStore(
            client=client,
            collection_name=self.collection_name,
            embedding=self.embeddings
        )
    
    def add_documents(self, documents: List[Document]):
        """
        Add documents to vector store and store for BM25 retrieval.
        
        Args:
            documents: List of Document objects (chunked PDFs)
        """
        # Store documents for BM25 (needs raw text)
        self.documents.extend(documents)
        
        # Add to vector store for dense embeddings
        self.vectorstore.add_documents(documents)
    
    def get_retriever(
        self, 
        k: int = 5, 
        use_hybrid: bool = False,
        use_bm25_only: bool = True,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5
    ):
        """
        Get retriever for RAG queries.
        
        **Default: BM25-only** (validated as best technique via RAGAS evaluation, composite score: 0.422)
        
        Based on evaluation results, BM25-only outperformed hybrid, dense-only, and parent-document
        retrieval for building code questions. Building codes benefit more from exact term matching
        (section numbers, citations) than semantic similarity.
        
        Args:
            k: Number of documents to retrieve
            use_hybrid: If True, use hybrid retrieval (BM25 + Dense). Overrides use_bm25_only.
            use_bm25_only: If True (default), use BM25-only retrieval. If False and use_hybrid=False, use dense-only.
            bm25_weight: Weight for BM25 results in hybrid ensemble (default 0.5)
            dense_weight: Weight for dense results in hybrid ensemble (default 0.5)
        
        Returns:
            LangChain retriever:
            - BM25Retriever if use_bm25_only=True (default)
            - EnsembleRetriever if use_hybrid=True
            - Dense retriever if use_bm25_only=False and use_hybrid=False
        
        Examples:
            # Default: BM25-only (validated best)
            retriever = vector_store.get_retriever(k=5)
            
            # Hybrid retrieval (BM25 + Dense)
            retriever = vector_store.get_retriever(k=5, use_hybrid=True)
            
            # Dense-only
            retriever = vector_store.get_retriever(k=5, use_bm25_only=False, use_hybrid=False)
        """
        # If hybrid requested, combine BM25 + Dense
        if use_hybrid and self.documents:
            # Setup BM25 retriever
            bm25_retriever = BM25Retriever.from_documents(
                self.documents, 
                k=k
            )
            
            # Setup dense retriever
            dense_retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": k}
            )
            
            # Combine using EnsembleRetriever (Reciprocal Rank Fusion)
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, dense_retriever],
                weights=[bm25_weight, dense_weight]
            )
            
            return hybrid_retriever
        
        # Default: BM25-only (validated best technique)
        elif use_bm25_only and self.documents:
            bm25_retriever = BM25Retriever.from_documents(
                self.documents,
                k=k
            )
            return bm25_retriever
        
        # Fallback: Dense-only (if BM25 not available or explicitly disabled)
        else:
            dense_retriever = self.vectorstore.as_retriever(
                search_kwargs={"k": k}
            )
            return dense_retriever
    
    def similarity_search(self, query: str, k: int = 5) -> List[Document]:
        """
        Direct similarity search (dense-only, without retriever).
        
        Note: This method only uses dense embeddings. For hybrid retrieval,
        use get_retriever() and call invoke() on the retriever.
        
        Args:
            query: Search query
            k: Number of results
        
        Returns:
            List of relevant Document objects
        """
        return self.vectorstore.similarity_search(query, k=k)