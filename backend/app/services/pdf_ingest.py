"""
PDF ingestion service: Load and chunk PDF documents.

Adapted from day_13 and day_9_A2A lesson patterns.
"""
from pathlib import Path
from typing import List
from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def load_pdf(file_path: str | Path) -> List[Document]:
    """
    Load a single PDF file.
    
    Pattern from day_13 lesson: PyMuPDFLoader for PDF loading.
    
    Args:
        file_path: Path to PDF file
    
    Returns:
        List of Document objects (one per page)
    """
    loader = PyMuPDFLoader(str(file_path))
    return loader.load()


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[Document]:
    """
    Split documents into chunks for embedding.
    
    Pattern from day_9_A2A lesson: RecursiveCharacterTextSplitter.
    
    Args:
        documents: List of Document objects
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunked Document objects
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    return text_splitter.split_documents(documents)


def ingest_pdf(
    file_path: str | Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[Document]:
    """
    Complete PDF ingestion: load + chunk.
    
    Convenience function combining load_pdf + chunk_documents.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunked Document objects ready for embedding
    """
    documents = load_pdf(file_path)
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)
    
    # Add source metadata to chunks
    source_name = Path(file_path).stem
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = source_name
        chunk.metadata["chunk_index"] = i
    
    return chunks