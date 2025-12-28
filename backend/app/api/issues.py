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