# backend/app/tests/test_integration_blueprint.py
"""Integration tests for blueprint extraction with compliance checking"""

import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

SAMPLE_PDFS = [
    "app/data/floor-plans/example_plan_01a.pdf",
    "app/data/floor-plans/example_plan_02.pdf",
]

def test_extract_and_check_endpoint():
    """Test the extract-and-check endpoint end-to-end"""
    pdf_path = Path(SAMPLE_PDFS[0])
    
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/blueprint/extract-and-check/",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={
                "generate_overlays": "true",
                "use_opencv": "false",
                "scale": "1.0"
            }
        )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify response structure
    assert "extraction" in data
    assert "issues" in data
    assert "summary" in data
    
    extraction = data["extraction"]
    assert "rooms" in extraction
    assert "confidence" in extraction
    assert "overlays" in extraction
    
    # Verify rooms extracted
    assert len(extraction["rooms"]) > 0
    
    # Verify overlays field exists (may be empty if OCR fails or no matches)
    # Overlay generation can fail gracefully, so we just check the field exists
    assert "overlays" in extraction
    assert isinstance(extraction["overlays"], list)
    
    # Verify compliance issues structure
    issues = data["issues"]
    assert isinstance(issues, list)
    
    # Verify summary
    summary = data["summary"]
    assert "total" in summary
    assert summary["total"] >= 0

def test_extract_endpoint_only():
    """Test basic extraction endpoint"""
    pdf_path = Path(SAMPLE_PDFS[0])
    
    if not pdf_path.exists():
        pytest.skip(f"Sample PDF not found: {pdf_path}")
    
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/blueprint/extract/",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"scale": "1.0"}
        )
    
    assert response.status_code == 200
    data = response.json()
    
    assert "rooms" in data
    assert "confidence" in data
    assert len(data["rooms"]) > 0

if __name__ == "__main__":
    pytest.main([__file__, "-v"])