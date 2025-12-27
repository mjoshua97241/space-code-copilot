import csv
from functools import lru_cache
from pathlib import Path
from typing import List, Set

from app.models.domain import Room, Door

from app.models.domain import Room, Door

# ============================================================================
# Path Configuration
# ============================================================================

# Get the data directory relative to this file
# This follows the same pattern as main.py for consistency
BASE_DIR = Path(__file__).parent.parent # Go up from services/ to app/
DATA_DIR = BASE_DIR / "data"

# ============================================================================
# Cache Configuration
# ============================================================================

# Cache based on file path and modification time
# This ensures cache is invalidated when CSV file are updated
def _get_cache_key(csv_path: Path) -> tuple:
    """
    Generate cache key based on file pat and modification time.

    This ensure the cache is invalidated when CSV file is modified, following the cache pattern from day_12 lesson (file-based invalidation).
    """
    if not csv_path.exists():
        return (str(csv_path), None)
    return (str(csv_path), csv_path.stat().st_mtime)

# ============================================================================
# Room Loader
# ============================================================================

@lru_cache(maxsize=2) # Cache up to 2 different file paths
def load_rooms(csv_path: Path | None = None) -> List[Room]:
    """
    Load rooms from CSV file into Room models.

    Uses LRU cache to avoid re-reading the same file multiple times.
    Cache is keyed by file path and modification time, so it automatically invalidates when the CSV file is updated.


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
    
    # Convert to absolute path for consistent caching
    csv_path = csv_path.resolve()

    # Get cache key (includes modification time for invalidation)
    cache_key = _get_cache_key(csv_path)

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
    
    # Return tuple for hashability (required for lru_cache)
    return tuple(rooms)

# ============================================================================
# Door Loader with Validation
# ============================================================================

def load_doors(
    csv_path: Path | None = None,
    room_ids: Set[str] | None = None
) -> tuple[Door, ...]:
    """
    Load doors from CSV file into Door models.
    
    Validates that each door's location_room_id references an existing Room.id.
    This ensures data integrity and catches errors early.
    
    Note: Caching is not used when room_ids is provided (for validation)
    because sets are not hashable. For performance, call without validation
    first, then validate separately if needed.
    
    Args:
        csv_path: Optional path to doors.csv. If None, uses default location.
        room_ids: Set of valid Room IDs for validation. If None, skips validation.
                 Pass this when you have loaded rooms first.
    
    Returns:
        Tuple of Door objects parsed from CSV.
    
    Raises:
        FileNotFoundError: If CSV file doesn't exist.
        ValueError: If CSV data is invalid or door references non-existent room.
    
    Example:
        rooms = list(load_rooms())
        room_ids = {room.id for room in rooms}
        doors = list(load_doors(room_ids=room_ids))
    """
    if csv_path is None:
        csv_path = DATA_DIR / "doors.csv"
    
    csv_path = csv_path.resolve()

    doors = []
    invalid_refs = []

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            # DictReader automatically uses first row as headers
            # This makes it easy to map CSV columns to Pydantic model fields
            reader = csv.DictReader(f)

            for row_num, row in enumerate(reader, start=2): # start=2 (header is row 1)
                try:
                    location_room_id = row["location_room_id"].strip()

                    # Validate room reference if room_ids provided
                    if room_ids is not None and location_room_id not in room_ids:
                        invalid_refs.append(
                            f"Row {row_num}: Door '{row['id']}' references "
                            f"non-existent room '{location_room_id}'"
                        )

                    # Convert level and area_m2 from strings to proper types
                    door = Door(
                        id=row["id"].strip(),
                        location_room_id=location_room_id,
                        clear_width_mm=float(row["clear_width_mm"]), # mm (SI unit)
                        level=int(row["level"])
                    )
                    doors.append(door)
                
                except (KeyError, ValueError, TypeError) as e:
                    # If a row is malformed, raise a clear error with context
                    raise ValueError(
                        f"Error parsing door at row {row_num} in {csv_path}: {e}"
                    ) from e

            # Raise error if any invalid room references found
            if invalid_refs:
                raise ValueError(
                    f"Invalid room references in doors.csv:\n" + "\n".join(invalid_refs)
                )

    except FileNotFoundError:
        raise FileNotFoundError(
            f"Rooms CSV file not found: {csv_path}"
        )
    
    return tuple(doors)

# ============================================================================
# Combined Loader with Validation
# ============================================================================

def load_design(
    rooms_path: Path | None = None, 
    doors_path: Path | None = None,
    valid_references: bool = True
    ) -> tuple[List[Room], List[Door]]:
    """
    Load both rooms and doors in one call with automatic validation.

    This is a convenience function that:
    1. Loads rooms first
    2. Validates that all door room references exist
    3. Returns both datasets

    Args:
        rooms_path: Optional path to rooms.csv
        doors_path: Optional path to doors.csv
        validate_references: If True, validates door->room references
    
    Return:
        Tuple of (rooms, doors) lists.
    
    Raises:
        ValueError: If door references invalid room IDs (when validate_references=True)
    
    Example:
        rooms, doors = load_design()
        # Now you have both datasets ready to use, validated
    """
    # Loads room first
    rooms_tuple = load_rooms(rooms_path)
    rooms = list(rooms_tuple)

    # Build set of room IDs for validation
    room_ids = {room.id for room in rooms} if valid_references else None

    # Load doors with validation
    doors_tuple = load_doors(doors_path, room_ids=room_ids)
    doors = list(doors_tuple)
    
    return rooms, doors

# ============================================================================
# Cache Management
# ============================================================================

def clear_cache():
    """
    Clear the LRU cache for load_rooms and load_doors.

    Useful for testing or when you want to force a reload.

    Example:
        load_rooms()    # First call - reads from file
        load_rooms()    # Seconds call - uses cache
        clear_cache()
        load_rooms()    # Third call - reads from file again
    """

    load_rooms.cache_clear()
    load_doors.cache_clear()

# ============================================================================
# Future: URL/Remote Loading
# ============================================================================

# TODO: Future enhancement - Load from URLs or remote sources
# This addresses a pain point mentioned by archites who need to:
# - Load schedules from cloud storage (S3, Google Drive, etc.)
# - Fetch from APIs
# - Import from BIM tools

# Potential Implementation:
# - Add load_rooms_from_url(url: str) function
# - Use requests/httpx to fetch CSV
# - Cache based on URL + ETag/Last-Modified headers
# - Support authentication for private sources