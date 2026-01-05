"""
End-to-end test suite for Code-Aware Space Planning Copilot.

Tests all features working together:
- Health endpoint
- Issues endpoint
- Chat endpoint
- PDF ingest
- Vector store retrieval
- Compliance checker
- Static files
- Frontend integration

Run with: uv run python app/tests/test_e2e.py
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any

# Add backend directory to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

# Load environment variables
from dotenv import load_dotenv
env_path = backend_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

from fastapi.testclient import TestClient
from app.main import app

# Test results tracking
test_results: List[Dict[str, Any]] = []

def log_test(name: str, passed: bool, message: str = "", details: Any = None):
    """Log test result."""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"   {message}")
    if details and not passed:
        print(f"   Details: {details}")
    test_results.append({
        "name": name,
        "passed": passed,
        "message": message,
        "details": details
    })
    print()

def test_health_endpoint(client: TestClient):
    """Test /health endpoint."""
    print("=" * 60)
    print("Testing Health Endpoint")
    print("=" * 60)
    
    try:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok"}
        log_test("Health Endpoint", True, f"Response: {data}")
    except Exception as e:
        log_test("Health Endpoint", False, str(e), response.text if 'response' in locals() else None)

def test_static_files(client: TestClient):
    """Test static file serving."""
    print("=" * 60)
    print("Testing Static Files")
    print("=" * 60)
    
    static_files = [
        "/static/plan.png",
        "/static/styles.css",
        "/static/overlays.json"
    ]
    
    for file_path in static_files:
        try:
            response = client.get(file_path)
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            if file_path.endswith(".json"):
                data = response.json()
                assert isinstance(data, list), "Overlays JSON should be a list"
                rooms = [o for o in data if o.get('type') != 'door']
                doors = [o for o in data if o.get('type') == 'door']
                log_test(f"Static File: {file_path}", True, f"Loaded {len(rooms)} rooms, {len(doors)} doors")
            else:
                log_test(f"Static File: {file_path}", True, f"Size: {len(response.content)} bytes")
        except Exception as e:
            log_test(f"Static File: {file_path}", False, str(e))

def test_frontend_template(client: TestClient):
    """Test frontend HTML template."""
    print("=" * 60)
    print("Testing Frontend Template")
    print("=" * 60)
    
    try:
        response = client.get("/")
        assert response.status_code == 200
        html = response.text
        assert "<html" in html.lower() or "<!doctype" in html.lower()
        assert "plan-image-wrapper" in html or "plan" in html.lower()
        assert "issues-list" in html.lower() or "issues" in html.lower()
        assert "chat" in html.lower()
        log_test("Frontend Template", True, "HTML template rendered successfully")
    except Exception as e:
        log_test("Frontend Template", False, str(e), response.text[:200] if 'response' in locals() else None)

def test_issues_endpoint(client: TestClient):
    """Test /api/issues endpoint."""
    print("=" * 60)
    print("Testing Issues Endpoint")
    print("=" * 60)
    
    try:
        response = client.get("/api/issues")
        assert response.status_code == 200
        issues = response.json()
        assert isinstance(issues, list), "Issues should be a list"
        
        # Check issue structure
        if issues:
            issue = issues[0]
            assert "element_id" in issue
            assert "element_type" in issue
            assert "rule_id" in issue
            assert "message" in issue
            assert "code_ref" in issue
        
        log_test("Issues Endpoint", True, f"Found {len(issues)} issues")
        
        # Test summary endpoint
        response = client.get("/api/issues/summary")
        assert response.status_code == 200
        summary = response.json()
        assert "total" in summary
        log_test("Issues Summary Endpoint", True, f"Total: {summary.get('total', 0)} issues")
        
    except Exception as e:
        log_test("Issues Endpoint", False, str(e), response.text if 'response' in locals() else None)

def test_chat_endpoint(client: TestClient):
    """Test /api/chat endpoint."""
    print("=" * 60)
    print("Testing Chat Endpoint")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        log_test("Chat Endpoint", False, "OPENAI_API_KEY not set - skipping chat test")
        return
    
    try:
        # Test simple query
        response = client.post(
            "/api/chat",
            json={"query": "What is the minimum bedroom area?"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "citations" in data
        assert isinstance(data["citations"], list)
        
        answer = data["answer"]
        assert len(answer) > 0, "Answer should not be empty"
        
        log_test("Chat Endpoint", True, f"Answer length: {len(answer)} chars, {len(data['citations'])} citations")
        
        # Check citation format
        if data["citations"]:
            citation = data["citations"][0]
            assert "source" in citation
            assert "page" in citation
            # Check for page type indicator
            page_str = str(citation["page"])
            has_page_type = "(PDF page)" in page_str or "(document page)" in page_str
            log_test("Citation Format", has_page_type, 
                    f"Citation: {citation.get('source', 'N/A')}, Page: {citation.get('page', 'N/A')}")
        
    except Exception as e:
        log_test("Chat Endpoint", False, str(e), response.text if 'response' in locals() else None)

def test_pdf_ingest():
    """Test PDF ingestion."""
    print("=" * 60)
    print("Testing PDF Ingest")
    print("=" * 60)
    
    pdf_path = backend_dir / "app" / "data" / "National-Building-Code.pdf"
    if not pdf_path.exists():
        # Try alternative name
        pdf_path = backend_dir / "app" / "data" / "code_sample.pdf"
    
    if not pdf_path.exists():
        log_test("PDF Ingest", False, f"PDF not found at {pdf_path}")
        return
    
    try:
        from app.services.pdf_ingest import ingest_pdf
        
        chunks = ingest_pdf(str(pdf_path))
        assert len(chunks) > 0, "Should have at least one chunk"
        
        # Check chunk metadata
        chunk = chunks[0]
        assert hasattr(chunk, 'page_content') or 'page_content' in chunk
        assert hasattr(chunk, 'metadata') or 'metadata' in chunk
        
        # Check for page numbers in metadata
        metadata = chunk.metadata if hasattr(chunk, 'metadata') else chunk.get('metadata', {})
        has_page_info = 'page' in metadata or 'page_pdf' in metadata
        
        log_test("PDF Ingest", True, f"Loaded {len(chunks)} chunks")
        log_test("PDF Metadata", has_page_info, f"Metadata keys: {list(metadata.keys())[:5]}")
        
    except Exception as e:
        log_test("PDF Ingest", False, str(e))

def test_vector_store():
    """Test vector store retrieval."""
    print("=" * 60)
    print("Testing Vector Store")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        log_test("Vector Store", False, "OPENAI_API_KEY not set - skipping vector store test")
        return
    
    try:
        from app.services.vector_store import VectorStore
        from app.services.pdf_ingest import ingest_pdf
        
        pdf_path = backend_dir / "app" / "data" / "National-Building-Code.pdf"
        if not pdf_path.exists():
            pdf_path = backend_dir / "app" / "data" / "code_sample.pdf"
        
        if not pdf_path.exists():
            log_test("Vector Store", False, "PDF not found - cannot test vector store")
            return
        
        # Create vector store
        vs = VectorStore()
        
        # Ingest PDF
        chunks = ingest_pdf(str(pdf_path))
        vs.add_documents(chunks)
        
        # Test BM25-only retrieval (default)
        retriever = vs.get_retriever(k=3, use_bm25_only=True)
        results = retriever.invoke("minimum bedroom area")
        
        assert len(results) > 0, "Should retrieve at least one result"
        assert len(results) <= 3, f"Should retrieve at most 3 results, got {len(results)}"
        
        log_test("Vector Store - BM25 Retrieval", True, f"Retrieved {len(results)} results")
        
        # Check result structure
        result = results[0]
        has_content = hasattr(result, 'page_content') or 'page_content' in result
        has_metadata = hasattr(result, 'metadata') or 'metadata' in result
        
        log_test("Vector Store - Result Structure", has_content and has_metadata, 
                "Results have content and metadata")
        
    except Exception as e:
        log_test("Vector Store", False, str(e))

def test_compliance_checker():
    """Test compliance checker."""
    print("=" * 60)
    print("Testing Compliance Checker")
    print("=" * 60)
    
    try:
        from app.services.design_loader import load_design
        from app.services.compliance_checker import check_compliance
        
        rooms, doors = load_design()
        assert len(rooms) > 0, "Should have at least one room"
        assert len(doors) > 0, "Should have at least one door"
        
        issues = check_compliance(rooms, doors)
        assert isinstance(issues, list), "Issues should be a list"
        
        log_test("Compliance Checker", True, 
                f"Checked {len(rooms)} rooms, {len(doors)} doors, found {len(issues)} issues")
        
        # Check issue structure
        if issues:
            issue = issues[0]
            assert hasattr(issue, 'element_id') or 'element_id' in issue
            assert hasattr(issue, 'message') or 'message' in issue
            log_test("Compliance Checker - Issue Structure", True, 
                    f"Sample issue: {issue.message[:50]}...")
        
    except Exception as e:
        log_test("Compliance Checker", False, str(e))

def test_rule_extraction():
    """Test rule extraction."""
    print("=" * 60)
    print("Testing Rule Extraction")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        log_test("Rule Extraction", False, "OPENAI_API_KEY not set - skipping rule extraction test")
        return
    
    try:
        from app.services.rules_seed import get_all_rules
        
        rules = get_all_rules()
        assert len(rules) > 0, "Should have at least one rule"
        
        # Check for seeded rules
        seeded_count = sum(1 for r in rules if r.id.startswith(('R00', 'D00')))
        extracted_count = len(rules) - seeded_count
        
        log_test("Rule Extraction", True, 
                f"Total: {len(rules)} rules ({seeded_count} seeded, {extracted_count} extracted)")
        
    except Exception as e:
        log_test("Rule Extraction", False, str(e))

def print_summary():
    """Print test summary."""
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    total = len(test_results)
    passed = sum(1 for r in test_results if r["passed"])
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print()
    
    if failed > 0:
        print("Failed Tests:")
        for result in test_results:
            if not result["passed"]:
                print(f"  - {result['name']}: {result['message']}")
        print()
    
    success_rate = (passed / total * 100) if total > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate == 100:
        print("\n🎉 All tests passed! System is ready for deployment.")
    elif success_rate >= 80:
        print("\n⚠️  Most tests passed. Review failures before deployment.")
    else:
        print("\n❌ Multiple test failures. Fix issues before deployment.")

def main():
    """Run all end-to-end tests."""
    print("\n" + "=" * 60)
    print("END-TO-END TEST SUITE")
    print("Code-Aware Space Planning Copilot")
    print("=" * 60 + "\n")
    
    # Create test client
    client = TestClient(app)
    
    # Run all tests
    test_health_endpoint(client)
    test_static_files(client)
    test_frontend_template(client)
    test_issues_endpoint(client)
    test_chat_endpoint(client)
    test_pdf_ingest()
    test_vector_store()
    test_compliance_checker()
    test_rule_extraction()
    
    # Print summary
    print_summary()
    
    # Return exit code
    failed = sum(1 for r in test_results if not r["passed"])
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())

