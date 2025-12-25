# Quick test
import sys
from pathlib import Path

# Add backend directory to path so 'app' module can be found
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.design_loader import load_rooms, load_doors, load_design

# Test individual loaders
rooms = load_rooms()
print(f"Loaded {len(rooms)} rooms")
print(rooms[0]) # Print first Room object

doors = load_doors()
print(f"Loaded {len(doors)} doors")
print(doors[0])

# Test combined loader
rooms, doors = load_design()
print(f"Design loaded: {len(rooms)} rooms, {len(doors)} doors")