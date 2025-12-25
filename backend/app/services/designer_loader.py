import csv
from pathlib import Path
from typing import List

from app.models.domain import Room, Door
from app.main import BASE_DIR

# ============================================================================
# Path Configuration
# ============================================================================

# Get the data directory relative to this file
# This follows the same pattern as main.py for consistency
BASE_DIR = Path(__file__).parent.parent # Go up from services/ to app/
DATA_DIR = BASE_DIR / "data"

# ============================================================================
# Room Loader
# ============================================================================

def load_rooms(csv_path: Path | None = None) -> List[Room]:
    """
    Load rooms from CSV file into Room models.

    Args:
        csv_path: Optional path to rooms.csv. If None, uses default location.

    Returns:
        List of Room objects parsed from CSV.
    
    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        ValueError: If CSV data is invalid (caught by Pydantic validation).    
    
    Example:
        rooms = load_rooms()
        # Returns: [Room(id="R101", name="North Bedroom", ...), ...]
    """

    if csv_path is None:
        csv_path = DATA_DIR / "rooms.csv"

    rooms = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # DictReader automatically uses first row as headers
            # This makes it easy to map CSV columns to Pydantic model fields
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2): # start=2 (header is row 1)
                try:
                    # Convert level and area_m2 from strings to proper types
                    room = Room(
                        id=row["id"].strip(),
                        name=row["name"].strip(),
                        type=row["type"].strip(),
                        level=int(row["level"]), # Convert string to int
                        area_m2=float(row["area_m2"]) # Convert string to float
                    )
                    rooms.append(room)
                
                except (KeyError, ValueError, TypeError) as e:
                    # If a row is malformed, raise a clear error with context
                    raise ValueError(
                        f"Error parsing room at row {row_num} in {csv_path}: {e}"
                    ) from e

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Rooms CSV file not found: {csv_path}"
        )
    
    return rooms

# ============================================================================
# Door Loader
# ============================================================================

def load_doors(csv_path: Path | None = None) -> List[Door]:
    """
    Load doors from CSV file into Door models.

    Args:
        csv_path: Optional path to doors.csv. If None, uses default location.
    
    Returns:
        List of Door objects parsed from CSV.

    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        ValueError: If CSV data is invalid (caught by Pydantic validation).    

    Example:
        doors = load_doors()
        # Returns: [Door(id="D1", location_room_id="R101", ...), ...]
    """

    if csv_path is None:
        csv_path = DATA_DIR / "doors.csv"

    doors = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # DictReader automatically uses first row as headers
            # This makes it easy to map CSV columns to Pydantic model fields
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2): # start=2 (header is row 1)
                try:
                    # Convert level and area_m2 from strings to proper types
                    door = Door(
                        id=row["id"].strip(),
                        location_room_id=row["location_room_id"].strip(),
                        clear_width_mm=row["clear_width_mm"].strip(), # mm (SI unit)
                        level=int(row["level"])
                    )
                    doors.append(door)
                
                except (KeyError, ValueError, TypeError) as e:
                    # If a row is malformed, raise a clear error with context
                    raise ValueError(
                        f"Error parsing door at row {row_num} in {csv_path}: {e}"
                    ) from e

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Rooms CSV file not found: {csv_path}"
        )
    
    return doors

# ============================================================================
# Combined Loader
# ============================================================================

def load_design(rooms_path: Path | None = None, doors_path: Path | None = None) -> tuple[List[Room], List[Door]]:
    """
    Load both rooms and doors in one call.

    This is a convenience function for when you need both datasets.
    Useful for the compliance checker which needs both.

    Args:
        rooms_path: Optional path to rooms.csv
        doors_path: Optional path to doors.csv
    
    Return:
        Tuple of (rooms, doors) lists.
    
    Example:
        rooms, doors = load_design()
        # Now you have both datasets ready to use
    """
    rooms = load_rooms(rooms_path)
    doors = load_doors(doors_path)
    return rooms, doors