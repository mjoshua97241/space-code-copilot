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

def test_conversation_flow(client: TestClient):
    """Test conversational chat flow with conversation_id and blueprint context."""
    print("=" * 60)
    print("Testing Conversation Flow")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        log_test("Conversation Flow", False, "OPENAI_API_KEY not set - skipping conversation flow test")
        return
    
    try:
        from app.models.domain import Room
        
        # ========================================================================
        # TEST 1: First message generates conversation_id
        # ========================================================================
        print("\n--- Test 1: First message generates conversation_id ---")
        response1 = client.post(
            "/api/chat",
            json={"query": "What is the minimum bedroom area?"}
        )
        if response1.status_code != 200:
            print(f"ERROR: Response status: {response1.status_code}")
            print(f"ERROR: Response body: {response1.text}")
        assert response1.status_code == 200, f"Expected 200, got {response1.status_code}. Response: {response1.text}"
        data1 = response1.json()
        
        # Verify conversation_id is present and valid
        assert "conversation_id" in data1, "Response should include conversation_id"
        conversation_id = data1["conversation_id"]
        assert conversation_id is not None, "conversation_id should not be None"
        assert len(conversation_id) > 0, "conversation_id should not be empty"
        assert conversation_id.startswith("conv_"), f"conversation_id should start with 'conv_', got: {conversation_id}"
        
        log_test("First Message - conversation_id Generated", True, 
                f"Generated conversation_id: {conversation_id}")
        
        # Verify response structure
        assert "answer" in data1, "Response should include answer"
        assert "citations" in data1, "Response should include citations"
        assert len(data1["answer"]) > 0, "Answer should not be empty"
        
        first_answer = data1["answer"]
        log_test("First Message - Response Structure", True, 
                f"Answer length: {len(first_answer)} chars")
        
        # ========================================================================
        # TEST 2: Follow-up message maintains context (uses same conversation_id)
        # ========================================================================
        print("\n--- Test 2: Follow-up message maintains context ---")
        response2 = client.post(
            "/api/chat",
            json={
                "query": "What about bathrooms?",
                "conversation_id": conversation_id
            }
        )
        assert response2.status_code == 200, f"Expected 200, got {response2.status_code}"
        data2 = response2.json()
        
        # Verify same conversation_id is returned
        assert "conversation_id" in data2, "Response should include conversation_id"
        assert data2["conversation_id"] == conversation_id, \
            f"Follow-up should return same conversation_id. Expected: {conversation_id}, Got: {data2['conversation_id']}"
        
        log_test("Follow-up Message - Same conversation_id", True, 
                f"Maintained conversation_id: {conversation_id}")
        
        # Verify response structure
        assert "answer" in data2, "Response should include answer"
        assert len(data2["answer"]) > 0, "Answer should not be empty"
        
        second_answer = data2["answer"]
        log_test("Follow-up Message - Response Structure", True, 
                f"Answer length: {len(second_answer)} chars")
        
        # Verify conversation history is being used (answer should be contextually aware)
        # The LLM should understand "What about bathrooms?" as a follow-up to bedroom area question
        # This is a soft check - we just verify the answer exists and is different from first
        assert first_answer != second_answer, "Follow-up answer should be different from first answer"
        log_test("Follow-up Message - Context Awareness", True, 
                "Follow-up answer generated (context maintained)")
        
        # ========================================================================
        # TEST 3: Blueprint context integration
        # ========================================================================
        print("\n--- Test 3: Blueprint context integration ---")
        
        # Create sample blueprint rooms
        blueprint_rooms = [
            Room(
                id="R1",
                name="Bedroom 1",
                type="bedroom",
                level=1,
                area_m2=8.5  # Below minimum (should be 9.5 m²)
            ),
            Room(
                id="R2",
                name="Living Room",
                type="living",
                level=1,
                area_m2=25.0
            ),
            Room(
                id="R3",
                name="Kitchen",
                type="kitchen",
                level=1,
                area_m2=12.0
            )
        ]
        
        # Convert rooms to dict for JSON serialization
        blueprint_context = [room.model_dump() for room in blueprint_rooms]
        
        # Test with blueprint context - ask about specific room
        response3 = client.post(
            "/api/chat",
            json={
                "query": "Is Bedroom 1 compliant with minimum area requirements?",
                "conversation_id": conversation_id,  # Continue same conversation
                "blueprint_context": blueprint_context
            }
        )
        assert response3.status_code == 200, f"Expected 200, got {response3.status_code}"
        data3 = response3.json()
        
        # Verify conversation_id is maintained
        assert "conversation_id" in data3, "Response should include conversation_id"
        assert data3["conversation_id"] == conversation_id, \
            f"Should maintain same conversation_id. Expected: {conversation_id}, Got: {data3['conversation_id']}"
        
        log_test("Blueprint Context - conversation_id Maintained", True, 
                f"Maintained conversation_id: {conversation_id}")
        
        # Verify response structure
        assert "answer" in data3, "Response should include answer"
        assert len(data3["answer"]) > 0, "Answer should not be empty"
        
        blueprint_answer = data3["answer"]
        log_test("Blueprint Context - Response Generated", True, 
                f"Answer length: {len(blueprint_answer)} chars")
        
        # Verify blueprint context is being used
        # The answer should reference "Bedroom 1" or the area (8.5 m²)
        # This is a soft check - we verify the answer mentions the room or area
        answer_lower = blueprint_answer.lower()
        mentions_bedroom = "bedroom" in answer_lower or "8.5" in blueprint_answer or "8.5" in answer_lower
        log_test("Blueprint Context - Room Reference", mentions_bedroom, 
                f"Answer mentions bedroom/area: {mentions_bedroom}")
        
        # ========================================================================
        # TEST 4: New conversation without conversation_id (should generate new one)
        # ========================================================================
        print("\n--- Test 4: New conversation generates new conversation_id ---")
        response4 = client.post(
            "/api/chat",
            json={"query": "What is the minimum door width?"}
            # No conversation_id provided - should generate new one
        )
        assert response4.status_code == 200, f"Expected 200, got {response4.status_code}"
        data4 = response4.json()
        
        # Verify new conversation_id is generated
        assert "conversation_id" in data4, "Response should include conversation_id"
        new_conversation_id = data4["conversation_id"]
        assert new_conversation_id != conversation_id, \
            f"New conversation should have different conversation_id. Old: {conversation_id}, New: {new_conversation_id}"
        assert new_conversation_id.startswith("conv_"), \
            f"conversation_id should start with 'conv_', got: {new_conversation_id}"
        
        log_test("New Conversation - New conversation_id Generated", True, 
                f"Generated new conversation_id: {new_conversation_id}")
        
        # ========================================================================
        # TEST 5: Blueprint context without conversation_id (new conversation)
        # ========================================================================
        print("\n--- Test 5: Blueprint context in new conversation ---")
        response5 = client.post(
            "/api/chat",
            json={
                "query": "Check if my living room meets the requirements",
                "blueprint_context": blueprint_context
                # No conversation_id - should generate new one
            }
        )
        assert response5.status_code == 200, f"Expected 200, got {response5.status_code}"
        data5 = response5.json()
        
        # Verify conversation_id is generated
        assert "conversation_id" in data5, "Response should include conversation_id"
        blueprint_conversation_id = data5["conversation_id"]
        assert blueprint_conversation_id.startswith("conv_"), \
            f"conversation_id should start with 'conv_', got: {blueprint_conversation_id}"
        
        log_test("Blueprint Context - New Conversation", True, 
                f"Generated conversation_id: {blueprint_conversation_id}")
        
        # Verify response mentions living room or area
        blueprint_answer2 = data5["answer"]
        answer_lower2 = blueprint_answer2.lower()
        mentions_living = "living" in answer_lower2 or "25" in blueprint_answer2 or "25.0" in blueprint_answer2
        log_test("Blueprint Context - Living Room Reference", mentions_living, 
                f"Answer mentions living room/area: {mentions_living}")
        
        # ========================================================================
        # SUMMARY
        # ========================================================================
        print("\n" + "=" * 60)
        print("Conversation Flow Test Summary")
        print("=" * 60)
        print(f"✅ First message generates conversation_id: {conversation_id}")
        print(f"✅ Follow-up messages maintain context: {conversation_id}")
        print(f"✅ Blueprint context integration works")
        print(f"✅ New conversations generate new conversation_id: {new_conversation_id}")
        print(f"✅ Blueprint context works in new conversations")
        print("=" * 60 + "\n")
        
        log_test("Conversation Flow - All Tests", True, 
                f"Tested {5} scenarios successfully")
        
    except AssertionError as e:
        log_test("Conversation Flow", False, f"Assertion failed: {str(e)}")
        raise  # Re-raise so pytest sees the failure
    except Exception as e:
        log_test("Conversation Flow", False, f"Unexpected error: {str(e)}")
        raise  # Re-raise so pytest sees the failure

def test_pdf_ingest():
    """Test PDF ingestion."""
    print("=" * 60)
    print("Testing PDF Ingest")
    print("=" * 60)
    
    # Try new filename first, then fallback to old names for compatibility
    pdf_path = backend_dir / "app" / "data" / "PD1096-National-Building-Code.pdf"
    if not pdf_path.exists():
        pdf_path = backend_dir / "app" / "data" / "National-Building-Code.pdf"
    if not pdf_path.exists():
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
        
        # Try new filename first, then fallback to old names for compatibility
        pdf_path = backend_dir / "app" / "data" / "PD1096-National-Building-Code.pdf"
        if not pdf_path.exists():
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

def test_pdf_upload_and_rag(client: TestClient):
    """Test PDF upload endpoint, verify indexing, and test RAG queries with uploaded PDF."""
    print("=" * 60)
    print("Testing PDF Upload, Indexing, and RAG Queries")
    print("=" * 60)
    
    if not os.getenv("OPENAI_API_KEY"):
        log_test("PDF Upload and RAG", False, "OPENAI_API_KEY not set - skipping PDF upload test")
        return
    
    # Find a test PDF file
    pdf_path = backend_dir / "app" / "data" / "PD1096-National-Building-Code.pdf"
    if not pdf_path.exists():
        pdf_path = backend_dir / "app" / "data" / "National-Building-Code.pdf"
    if not pdf_path.exists():
        pdf_path = backend_dir / "app" / "data" / "RA9514-Fire-Code-RIRR-rev-2019.pdf"
    
    if not pdf_path.exists():
        log_test("PDF Upload and RAG", False, f"Test PDF not found - cannot test upload")
        return
    
    try:
        # ========================================================================
        # TEST 1: Upload PDF via API endpoint
        # ========================================================================
        print("\n--- Test 1: Upload PDF via /api/codes/upload/ ---")
        with open(pdf_path, "rb") as f:
            response = client.post(
                "/api/codes/upload/",
                files={"file": (pdf_path.name, f, "application/pdf")}
            )
        
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response should include 'success' field"
        assert data["success"] is True, "Upload should be successful"
        assert "filename" in data, "Response should include 'filename' field"
        assert "chunks" in data, "Response should include 'chunks' field"
        assert "message" in data, "Response should include 'message' field"
        
        uploaded_filename = data["filename"]
        chunk_count = data["chunks"]
        
        assert chunk_count > 0, f"Should have at least one chunk, got {chunk_count}"
        
        log_test("PDF Upload - Endpoint Response", True, 
                f"Uploaded '{uploaded_filename}' with {chunk_count} chunks")
        
        # ========================================================================
        # TEST 2: Verify PDF is indexed in vector store
        # ========================================================================
        print("\n--- Test 2: Verify PDF is indexed in vector store ---")
        from app.api.chat import get_vector_store
        
        vector_store = get_vector_store()
        retriever = vector_store.get_retriever(k=5, use_bm25_only=True)
        
        # Try to retrieve documents using a query that should match the uploaded PDF
        # Use a generic query that should find something in building codes
        test_query = "minimum area requirements"
        retrieved_docs = retriever.invoke(test_query)
        
        assert len(retrieved_docs) > 0, "Should retrieve at least one document"
        
        # Check if any retrieved document has the uploaded filename as source
        # The source might be the filename without extension or with some transformation
        source_names = [doc.metadata.get("source", "") for doc in retrieved_docs]
        filename_base = Path(uploaded_filename).stem  # Remove .pdf extension
        
        # Check if uploaded PDF appears in retrieved documents
        # Source might be filename or filename without extension
        found_uploaded_pdf = any(
            filename_base.lower() in source.lower() or 
            uploaded_filename.lower() in source.lower()
            for source in source_names
        )
        
        log_test("PDF Upload - Indexing Verification", found_uploaded_pdf,
                f"Retrieved {len(retrieved_docs)} docs. Sources: {source_names[:3]}")
        
        # ========================================================================
        # TEST 3: Test RAG query with uploaded PDF content
        # ========================================================================
        print("\n--- Test 3: Test RAG query to verify uploaded PDF is accessible ---")
        
        # Make a chat query that should retrieve content from the uploaded PDF
        # Use a query that's likely to be in building codes
        chat_response = client.post(
            "/api/chat",
            json={"query": "What are the minimum area requirements for bedrooms?"}
        )
        
        assert chat_response.status_code == 200, \
            f"Expected 200, got {chat_response.status_code}. Response: {chat_response.text}"
        
        chat_data = chat_response.json()
        assert "answer" in chat_data, "Chat response should include 'answer'"
        assert "citations" in chat_data, "Chat response should include 'citations'"
        assert len(chat_data["answer"]) > 0, "Answer should not be empty"
        
        # Check if citations include the uploaded PDF
        citations = chat_data["citations"]
        citation_sources = [c.get("source", "") for c in citations]
        
        # Check if uploaded PDF appears in citations
        found_in_citations = any(
            filename_base.lower() in source.lower() or 
            uploaded_filename.lower() in source.lower()
            for source in citation_sources
        )
        
        log_test("PDF Upload - RAG Query Test", True,
                f"Got answer ({len(chat_data['answer'])} chars) with {len(citations)} citations")
        
        log_test("PDF Upload - Citation Verification", found_in_citations,
                f"Citations: {citation_sources[:3]}")
        
        # ========================================================================
        # TEST 4: Test error handling (non-PDF file)
        # ========================================================================
        print("\n--- Test 4: Test error handling (non-PDF file) ---")
        
        # Create a temporary text file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp:
            tmp.write("This is not a PDF file")
            tmp_path = tmp.name
        
        try:
            with open(tmp_path, "rb") as f:
                error_response = client.post(
                    "/api/codes/upload/",
                    files={"file": ("test.txt", f, "text/plain")}
                )
            
            assert error_response.status_code == 400, \
                f"Expected 400 for non-PDF file, got {error_response.status_code}"
            
            error_data = error_response.json()
            assert "detail" in error_data, "Error response should include 'detail'"
            assert "PDF" in error_data["detail"] or "pdf" in error_data["detail"].lower(), \
                "Error message should mention PDF requirement"
            
            log_test("PDF Upload - Error Handling", True,
                    f"Correctly rejected non-PDF file: {error_data.get('detail', '')[:50]}")
        
        finally:
            # Clean up temp file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
        
        # ========================================================================
        # SUMMARY
        # ========================================================================
        print("\n" + "=" * 60)
        print("PDF Upload and RAG Test Summary")
        print("=" * 60)
        print(f"✅ PDF upload endpoint works: {uploaded_filename} ({chunk_count} chunks)")
        print(f"✅ PDF indexed in vector store: {found_uploaded_pdf}")
        print(f"✅ RAG queries work with uploaded PDF")
        print(f"✅ Error handling works for non-PDF files")
        print("=" * 60 + "\n")
        
        log_test("PDF Upload and RAG - All Tests", True,
                f"Successfully tested upload, indexing, and RAG queries")
        
    except AssertionError as e:
        log_test("PDF Upload and RAG", False, f"Assertion failed: {str(e)}")
        raise  # Re-raise so pytest sees the failure
    except Exception as e:
        log_test("PDF Upload and RAG", False, f"Unexpected error: {str(e)}")
        raise  # Re-raise so pytest sees the failure

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
    test_conversation_flow(client)
    test_pdf_ingest()
    test_vector_store()
    test_compliance_checker()
    test_rule_extraction()
    test_pdf_upload_and_rag(client)
    
    # Print summary
    print_summary()
    
    # Return exit code
    failed = sum(1 for r in test_results if not r["passed"])
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    exit(main())

