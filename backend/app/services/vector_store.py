"""
Vector store service: Embeddings + Qdrant for RAG retrieval with Hybrid Retrieval (BM25 + Dense).

Adapted from:
- day_12: CacheBackedEmbeddings for embedding caching
- day_9_A2A: QdrantVectorStore setup
- day_13: Hybrid retrieval pattern (BM25 + Dense via EnsembleRetriever)
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
    Vector store with caching and hybrid retrieval (BM25 + Dense) for building code PDFs.
    
    Hybrid retrieval combines:
    - BM25: Exact term matching (section numbers, citations, legal phrases)
    - Dense embeddings: Semantic similarity (paraphrases, related concepts)
    
    Pattern adapted from:
    - day_12: CacheBackedEmbeddings for embedding caching
    - day_9_A2A: QdrantVectorStore setup
    - day_13: Hybrid retrieval via EnsembleRetriever
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
        use_hybrid: bool = True,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5
    ):
        """
        Get retriever for RAG queries.
        
        By default, returns hybrid retriever (BM25 + Dense) for better building code retrieval.
        BM25 catches exact terms (section numbers, citations), dense catches semantic meaning.
        
        Args:
            k: Number of documents to retrieve from each retriever (before merging)
            use_hybrid: If True, use hybrid retrieval (BM25 + Dense). If False, dense-only.
            bm25_weight: Weight for BM25 results in ensemble (default 0.5)
            dense_weight: Weight for dense results in ensemble (default 0.5)
        
        Returns:
            LangChain retriever (EnsembleRetriever for hybrid, or dense-only retriever)
        """
        # Dense retriever (always available)
        dense_retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": k}
        )
        
        # If hybrid and we have documents, combine BM25 + Dense
        if use_hybrid and self.documents:
            # Setup BM25 retriever (day_13 pattern)
            # BM25Retriever needs documents to build its index
            bm25_retriever = BM25Retriever.from_documents(
                self.documents, 
                k=k
            )
            
            # Combine using EnsembleRetriever (day_13 pattern)
            # EnsembleRetriever merges results using Reciprocal Rank Fusion (RRF)
            hybrid_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, dense_retriever],
                weights=[bm25_weight, dense_weight]  # Equal weighting by default
            )
            
            return hybrid_retriever
        else:
            # Fallback to dense-only (backward compatible)
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