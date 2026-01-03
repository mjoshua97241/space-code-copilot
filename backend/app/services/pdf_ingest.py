"""
PDF ingestion service: Load and chunk PDF documents.

Adapted from day_13 and day_9_A2A lesson patterns.
"""
import re
from pathlib import Path
from typing import List, Optional
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


def extract_section_number(text: str) -> Optional[str]:
    """
    Extract section number from text using regex patterns.
    
    Looks for patterns like:
    - "Section 5.2.3" or "Section 5.2.3.1"
    - "Chapter 5" or "Chapter 5.2"
    - "Art. 5.2.3" (Article)
    - "§ 5.2.3" (Section symbol)
    
    Args:
        text: Text to search for section numbers
    
    Returns:
        Section number string (e.g., "5.2.3") or None if not found
    """
    # Pattern 1: "Section X.X.X" or "Section X.X.X.X"
    section_pattern = r'(?:Section|Sec\.?)\s+(\d+(?:\.\d+){1,3})'
    match = re.search(section_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 2: "Chapter X" or "Chapter X.X"
    chapter_pattern = r'Chapter\s+(\d+(?:\.\d+)?)'
    match = re.search(chapter_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 3: "Art. X.X.X" or "Article X.X.X"
    article_pattern = r'(?:Art\.?|Article)\s+(\d+(?:\.\d+){1,2})'
    match = re.search(article_pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Pattern 4: "§ X.X.X" (section symbol)
    symbol_pattern = r'§\s*(\d+(?:\.\d+){1,3})'
    match = re.search(symbol_pattern, text)
    if match:
        return match.group(1)
    
    return None


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[Document]:
    """
    Split documents into chunks for embedding.
    
    Preserves page numbers from original documents and extracts section numbers.
    
    Pattern from day_9_A2A lesson: RecursiveCharacterTextSplitter.
    
    Args:
        documents: List of Document objects (from PyMuPDFLoader, includes page metadata)
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunked Document objects with preserved page numbers and extracted section numbers
    """
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)
    
    # Preserve page numbers and extract section numbers
    for chunk in chunks:
        # Preserve page number from original document (PyMuPDFLoader provides 0-indexed page)
        if "page" in chunk.metadata:
            # Convert 0-indexed to 1-indexed for human readability
            page_num = chunk.metadata.get("page", 0)
            if isinstance(page_num, int):
                chunk.metadata["page"] = page_num + 1
        else:
            # If page not in metadata, try to get from original document
            # (This shouldn't happen with PyMuPDFLoader, but handle gracefully)
            chunk.metadata["page"] = None
        
        # Extract section number from chunk text
        section = extract_section_number(chunk.page_content)
        if section:
            chunk.metadata["section"] = section
        else:
            chunk.metadata["section"] = None
    
    return chunks


def ingest_pdf(
    file_path: str | Path,
    chunk_size: int = 1000,
    chunk_overlap: int = 100
) -> List[Document]:
    """
    Complete PDF ingestion: load + chunk with enhanced metadata.
    
    Convenience function combining load_pdf + chunk_documents.
    Adds source, page numbers, and section numbers to chunk metadata.
    
    Args:
        file_path: Path to PDF file
        chunk_size: Target chunk size
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunked Document objects ready for embedding with metadata:
        - source: PDF filename (without extension)
        - chunk_index: Sequential chunk number
        - page: Page number (1-indexed, from PyMuPDFLoader)
        - section: Section number if found (e.g., "5.2.3") or None
    """
    documents = load_pdf(file_path)
    chunks = chunk_documents(documents, chunk_size, chunk_overlap)
    
    # Add source metadata to chunks
    source_name = Path(file_path).stem
    for i, chunk in enumerate(chunks):
        chunk.metadata["source"] = source_name
        chunk.metadata["chunk_index"] = i
        # page and section are already set by chunk_documents()
    
    return chunks