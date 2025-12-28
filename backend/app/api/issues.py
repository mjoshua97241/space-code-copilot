from fastapi import APIRouter, HTTPException
from typing import List

from app.models.domain import Issue
from app.services.design_loader import load_design
from app.services.compliance_checker import check_compliance

# ============================================================================
# API Router Setup
# ============================================================================

# Create a router for issues-related endpoints
# This follows FastAPI best practice: group related routes
APIRouter(
    prefix="/api/issues",
    tags=["issues"] # Group endpoints in API docs
)

# ============================================================================
# GET /api/issues Endpoint
# ============================================================================

@router.get("/", response_model=List[Issue])
def get_issues() -> List[Issue]:
    """
    Get all compliance issues for the current design.

    This endpoint:
    1. Loads roooms and doors from CSV files
    2. Runs compliance checker against all rules
    3. Returns list of Issue objects for any violations found

    **Design decisions:**
    - Loads data fresh on each request (CSV files may change)
    - Uses `response_model=List[Issue]` for automatic Pydantic serialization
    - returns empty list if design is fully compliant

    Returns:
        List of Issue objects representing compliance violations.
        Empty list if design is compliant.

    Raises:
        HTTPException: If CSV files are missing or invalid

    Example response:
        [
            {
                "element_id": "D1",
                "element_type": "door",
                "rule_id": "DOO1",
                "message": "Door 'D1' has clear widht 750mm, but minimum required is 800 mm...,
                "code_ref": "NBC Section 8.3.2 - Accessible door clear width,
                "severity": "error"
            },
            ...
        ]
    """
    try:
        # Load design data (rooms and doors from CSV)
        rooms, doors = load_design()

        # Checl compliance against all rules
        issues = check_compliance(rooms, doors)

        # Return issues (FastAPI automatically serializes Pydantic models to JSON)
        return issues

    except FileNotFoundError as e:
        # Handle missing CSV files
        raise HTTPException(
            status_code=404,
            detail=f"Design data not found: {str(e)}"
        )

    except ValueError as e:
        # Handle validation errors (e.g., invalid CSV data)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid design data: {str(e)}"
        )

    except Exception as e:
        # Catch-all for unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

# ============================================================================
# GET /api/issues/summary Endpoint (Optional Helper)
# ============================================================================

@router.get("/summary")
def get_issues_summary() -> dict:
    """
    Get a summary of compliance issues (counts by type, severity).

    Useful for UI to show quick statistics without loading all issue details.

    Returns:
        Dictionary with summary statistics:
        {
            "total": 2,
            "by_element_type": {"room": 0, "door": 2},
            "by_severity": {"error": 2, "warning": 0}
        }
    """
    try:
        from app.services.compliance_checker import get_compliance_summary

        rooms, doors = load_design()
        issues = check_compliance(rooms, doors)
        summary = get_compliance_summary(issues)

        return summary

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error generating summary: {str(e)}"
        )