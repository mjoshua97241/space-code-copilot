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


def extract_page_number_from_text(text: str, pdf_page_index: int) -> Optional[int]:
    """
    Extract the actual page number from document text (footer/header).
    
    Looks for page numbers in common locations:
    - Bottom center/right: "100" or "Page 100"
    - Top right: "100" or "Page 100"
    - Footer patterns: standalone numbers at end of lines
    
    Args:
        text: Page content text
        pdf_page_index: PDF page index (0-indexed) as reference for validation
    
    Returns:
        Extracted page number (as integer) or None if not found
    """
    if not text:
        return None
    
    lines = text.split('\n')
    pdf_page_num = pdf_page_index + 1  # Convert to 1-indexed for comparison
    
    # Pattern 1: "Page X" or "p. X" in footer (last 200 chars)
    # This is the most reliable pattern - explicit page number label
    footer_text = text[-200:] if len(text) > 200 else text
    footer_pattern = r'(?:Page|p\.?)\s*(\d+)\b'
    matches = re.findall(footer_pattern, footer_text, re.IGNORECASE)
    for match in matches:
        page_num = int(match)
        # Validate: reasonable range (max 2000 for very large documents)
        # For explicit "Page X" pattern, be more lenient but still reasonable
        if 1 <= page_num <= 2000:
            return page_num
    
    # Pattern 2: Standalone number at end of last 3 lines (common footer format)
    # Conservative: only last 3 lines, must be short
    for line in reversed(lines[-3:]):
        line = line.strip()
        # Check if line is just a number and very short (footer page numbers are usually 1-4 digits)
        if line.isdigit() and len(line) <= 4:
            page_num = int(line)
            # Validate: reasonable range (1-2000)
            # For standalone numbers, require them to be within ±100 of PDF page
            # (allows for TOC/cover pages but filters out obviously wrong numbers)
            if 1 <= page_num <= 2000 and abs(page_num - pdf_page_num) <= 100:
                return page_num
    
    # Pattern 3: Number at very end of last line (right-aligned footer)
    # Conservative: only last line, must be short
    if lines:
        last_line = lines[-1].strip()
        # Look for number at very end of line
        end_match = re.search(r'(\d+)\s*$', last_line)
        if end_match:
            page_num = int(end_match.group(1))
            # Validate: reasonable range, short line, max 4 digits, within ±100 of PDF page
            if (1 <= page_num <= 2000 and len(last_line) < 30 and 
                len(end_match.group(1)) <= 4 and abs(page_num - pdf_page_num) <= 100):
                return page_num
    
    return None


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
    Extracts document page numbers from full pages (before chunking) for accuracy.
    
    Pattern from day_9_A2A lesson: RecursiveCharacterTextSplitter.
    
    Args:
        documents: List of Document objects (from PyMuPDFLoader, includes page metadata)
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
    
    Returns:
        List of chunked Document objects with preserved page numbers and extracted section numbers
    """
    # First, extract document page numbers from full pages (more accurate)
    # Map PDF page index to document page number
    page_number_map = {}  # pdf_page_index -> document_page_number
    for doc in documents:
        pdf_page_index = doc.metadata.get("page", 0)
        if isinstance(pdf_page_index, int):
            # Extract page number from full page text (more reliable than chunks)
            page_doc = extract_page_number_from_text(doc.page_content, pdf_page_index)
            if page_doc:
                # Validate: page number should be reasonable (not obviously wrong)
                # Max reasonable page number: 5000 (very large documents)
                if 1 <= page_doc <= 5000:
                    page_number_map[pdf_page_index] = page_doc
    
    # Now chunk the documents
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )
    chunks = text_splitter.split_documents(documents)
    
    # Preserve page numbers and extract section numbers
    for chunk in chunks:
        # Get PDF page index (PyMuPDFLoader provides 0-indexed page)
        pdf_page_index = chunk.metadata.get("page", 0)
        if isinstance(pdf_page_index, int):
            # Store PDF page number (1-indexed for human readability)
            chunk.metadata["page_pdf"] = pdf_page_index + 1
        else:
            chunk.metadata["page_pdf"] = None
        
        # Use document page number from map (extracted from full page)
        if pdf_page_index in page_number_map:
            chunk.metadata["page_document"] = page_number_map[pdf_page_index]
        else:
            chunk.metadata["page_document"] = None
        
        # For backward compatibility, set "page" to document page if available, otherwise PDF page
        chunk.metadata["page"] = chunk.metadata.get("page_document") or chunk.metadata.get("page_pdf")
        
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
        - page_pdf: PDF page number (1-indexed, from PyMuPDFLoader)
        - page_document: Document page number (extracted from text, if found)
        - page: Preferred page number (document page if available, otherwise PDF page)
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