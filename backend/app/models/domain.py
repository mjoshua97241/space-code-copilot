from pydantic import BaseModel, Field
from typing import Literal, Optional

# ==================================================================
# Room Model
# ==================================================================

class Room(BaseModel):
    """
    Represents a room in the building design.

    Maps directly to rooms.csv columns:
    - id: Unique identifier (e.g., "R101")
    - name: Human-readable name (e.g., "North Bedroom")
    - type: Room category (bedroom, living, etc.)
    - level: Floor level (integer)
    - area_m2: Area in square meters (SI unit)
    """
    id: str = Field(..., description="Unique room identifier")
    name: str = Field(..., description="Room name")
    type: str = Field(..., description="Room type/category")
    level: int = Field(..., ge=1, description="Floor level (1-based)")
    area_m2: float = Field(..., gt=0, description="Area in square meters")

    class Config:
        # Allows using field names from CSV directly
        # Example: Room(id="R101", name="North Bedroom", ...)
        frozen = False # Can modify after creation if needed

# ==================================================================
# Door Model
# ==================================================================

class Door(BaseModel):
    """
    Represents a door in the building design.

    Maps directly to doors.csv columns:
    - id: Unique identifier (e.g., "D1")
    - location_room_id: Which room this door belongs to (references Room.id)
    - clear_width_mm: Minimum clear opening width in millimeters (SI unit)
    - level: Floor level (integer)

    Note: clear_width_mm is millimeters (mm) per building code standards, even though other measurements use meters. This is common in AEC.
    """
    id: str = Field(..., description="Unique door identifier")
    location_room_id: str = Field(..., description="Room ID this door belongs to")
    clear_width_mm: float = Field(..., gt=0, description="Clear width in millimeters")
    level: int = Field(..., ge=1, description="Floor level (1-based)")

    class Config:
        frozen = False

# ==================================================================
# Rule Model
# ==================================================================

class Rule(BaseModel):
    """
    Represents a building code rule or standard.

    Rules can be:
    1. Seeded (hardcoded for initial MVP) - e.g., "Bedrooms must be >= 9.5 m²"
    2. Extracted from PDFs (MVP core feature) - via LLM extraction from code PDFs

    The rule_type determines how the rule is checked:
    - "area_min": Minimum area requirement (for rooms)
    - "width_min": Minimum width requirement (for doors)
    - "text": Text-based rule requiring LLM interpretation
    """
    id: str = Field(..., description="Unique rule identifier")
    name: str = Field(..., description="Rule name/description")
    rule_type: Literal["area_min", "width_min", "text"] = Field(
        ..., 
        description="Type of rule (determines how it's checked)"
    )
    element_type: Literal["room", "door"] = Field(
        ...,
        description="What element type this rule applies to"
    )
    # For numeric rules (area_min, width_min)
    min_value: Optional[float] = Field(
        None,
        gt=0,
        description="Minimum value (in SI units: m² for area, mm for width)"
    )
    # For text-based rules (future)
    rule_text: Optional[str] = Field(
        None,
        description="Text description of the rule (for LLM interpretation)"
    )
    code_ref: Optional[str] = Field(
        None,
        description="Building code reference (e.g., 'IBC 2021 Section 3.2.1')"
    )

    class Config:
        frozen = False

# ==================================================================
# Issue Model
# ==================================================================

class Issue(BaseModel):
    """
    Represents a compliance violation found by the compliance checker.

    This is the output of checking Room/Door against Rules.
    Returned by /api/issues endpoint.

    Fields:
    - element_id: Which Room.id or Door.id has the issue
    - element_type: "room" or "door" (matches Rule.element_type)
    - rule_id: Which Rule was violated
    - message: Human-readable description of the violation
    - code_ref: Building code reference (copied from Rule.code_ref)
    - severity: Optional severity level (for future use)
    """
    element_id: str = Field(..., description="ID of the non-compliant element")
    element_type: Literal["room", "door"] = Field(
        ...,
        description="Type of element with the issue"
    )
    rule_id: str = Field(..., description="ID of the violated rule")
    message: str = Field(..., description="Human-readable violation message")
    code_ref: Optional[str] = Field(
        None,
        description="Building code reference"
    )
    severity: Optional[Literal["error", "warning"]] = Field(
        "error",
        description="Severity level (default: error)"
    )

    class Config:
        frozen = False
