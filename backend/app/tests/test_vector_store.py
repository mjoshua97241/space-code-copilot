"""
Test vector store with hybrid retrieval (BM25 + Dense).

Run with: uv run python app/tests/test_vector_store.py

Requires:
- OPENAI_API_KEY environment variable set
- PDF file at app/data/National-Building-Code.pdf
"""
import sys
import os
from pathlib import Path

# Add backend directory to path so 'app' module can be found
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables if .env exists
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from app.services.vector_store import VectorStore
from app.services.pdf_ingest import ingest_pdf

def main():
    """Test hybrid retrieval."""
    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it in your .env file or export it:")
        print("  export OPENAI_API_KEY='your-key-here'")
        return
    
    print("Creating vector store...")
    vs = VectorStore()
    
    # Check if PDF exists
    pdf_path = backend_dir / "app" / "data" / "National-Building-Code.pdf"
    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        print("Please ensure the PDF file exists in app/data/")
        return
    
    print(f"Loading PDF from {pdf_path}...")
    chunks = ingest_pdf(str(pdf_path))
    print(f"Loaded {len(chunks)} chunks")
    
    print("Adding documents to vector store...")
    vs.add_documents(chunks)
    
    print("Getting hybrid retriever (BM25 + Dense)...")
    retriever = vs.get_retriever(k=5)
    
    # Test query
    query = "What is the minimum bedroom area?"
    print(f"\nQuery: {query}")
    results = retriever.invoke(query)
    print(f"Found {len(results)} results\n")
    
    # Show first result
    if results:
        print("First result:")
        print(f"  Content: {results[0].page_content[:200]}...")
        if results[0].metadata:
            print(f"  Metadata: {results[0].metadata}")

if __name__ == "__main__":
    main()