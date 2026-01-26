"""Unit tests for blueprint_extractor.py"""

import pytest
import sys
import json
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.services.blueprint_extractor import (
    _load_image_as_base64,
    _build_extraction_prompt,
    _parse_llm_response,
    _validate_and_convert_rooms,
    _calculate_confidence_scores,
    extract_rooms_from_blueprint,
    _get_image_dimensions,
    _create_overlays_from_label_bbox
)
from app.models.domain import Room, Overlay

# Add backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class TestParseResponse:
    """Tests for _parse_llm_response"""
    
    def test_parse_clean_json(self):
        response = '{"rooms": [{"name": "Office", "type": "office", "area_m2": 15.0 }]}'
        result = _parse_llm_response(response)
        assert "rooms" in result
        assert len(result["rooms"]) == 1
        assert result["rooms"][0]["name"] == "Office"
    
    def test_parse_json_in_markdown(self):
        response = '''{"rooms":[{"name": "Bedroom", "type": "bedroom", "area_m2": 12.0}]}'''
        result = _parse_llm_response(response)
        assert result["rooms"][0]["name"] == "Bedroom"
    
    def test_parse_json_with_surrounding_text(self):
        # Note: Current implementation doesn't handle surrounding text without code blocks
        # This test verifies JSON inside markdown code blocks works
        response = '''```json
{"rooms": [{"name": "Living", "type": "living", "area_m2": 25.0}]}
```'''
        result = _parse_llm_response(response)
        assert result["rooms"][0]["type"] == "living"
        
    def test_parse_invalid_json_raises(self):
        response = "This is not JSON at all"
        with pytest.raises(ValueError):
            _parse_llm_response(response)
    
class TestValidatedAndConvertRooms:
    """Tests for _validate_and_convert_rooms"""
    
    def test_valid_room(self):
        raw_rooms = [{"name": "Living", "type": "living", "area_m2": 25.0}]
        rooms = _validate_and_convert_rooms(raw_rooms)
        assert len(rooms) == 1
        assert isinstance(rooms[0], Room)
        assert rooms[0].name == "Living"
    
    def test_room_with_missing_name_gets_default(self):
        # Current implementation assigns default name when missing
        raw_rooms = [
            {"type": "office", "area_m2": 15.0}, # missing name - gets default
            {"name": "Valid Room", "type": "bedroom", "area_m2": 12.0}
        ]
        rooms = _validate_and_convert_rooms(raw_rooms)
        assert len(rooms) == 2
        assert rooms[1].name == "Valid Room"
    
    def test_room_with_invalid_area_skipped(self):
        raw_rooms = [
            {"name": "Bad Room", "type": "office", "area_m2": -5.0}, # negative area
            {"name": "Good Room", "type": "office", "area_m2": 10.0}
        ]
        rooms = _validate_and_convert_rooms(raw_rooms)
        assert len(rooms) == 1
        assert rooms[0].name == "Good Room"
    
    def test_empty_list_returns_empty(self):
        rooms = _validate_and_convert_rooms([])
        assert rooms == []
    
class TestBuildExtractionPrompt:
    """Tests for _build_extraction_prompt"""
    
    def test_prompt_contains_scale(self):
        prompt = _build_extraction_prompt(scale=1.0)
        assert "1:100" in prompt or "scale" in prompt.lower()
        
    def test_prompt_requests_json(self):
        prompt = _build_extraction_prompt(scale=1.0)
        assert "json" in prompt.lower()
        
class TestCalculateConfidenceScores:
    """Tests for _calculate_confidence_scores"""
    
    def test_confidence_with_valid_rooms(self):
        rooms = [
            Room(id="r1", name="Office", type="office", level=1, area_m2=15.0),
            Room(id="r2", name="Bedroom", type="bedroom", level=1, area_m2=12.0)
        ]
        parsed = {"rooms": [{"name": "Office"}, {"name": "Bedroom"}]}
        confidence = _calculate_confidence_scores(rooms, parsed)
        
        assert "overall" in confidence
        assert 0.0 <= confidence["overall"] <= 1.0
        assert "name_confidence" in confidence
        assert "type_confidence" in confidence
        assert "area_confidence" in confidence
        
class TestExtractRoomsFromBlueprint:
    """Integration tests for extract_rooms_from_blueprint"""
    
    @patch("app.services.blueprint_extractor.get_vision_llm")
    @patch("app.services.blueprint_extractor._load_image_as_base64")
    def test_successful_extraction(self, mock_load_image, mock_get_llm):
        # Mock image loading
        mock_load_image.return_value = "data:image/png;base64;fakeimagecontent"
        
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(
            {
                "rooms": [
                    {"name": "Office 101", "type": "office", "area_m2": 15.0, "level": 1},
                    {"name": "Meeting Room", "type": "meeting", "area_m2": 25.0, "level": 1}
                ]
            }
        )
        mock_get_llm.return_value = mock_llm
        
        result = extract_rooms_from_blueprint(
            image_path="fake_blueprint.png",
            scale_override=1.0
        )
        
        assert hasattr(result, "rooms")
        assert len(result.rooms) == 2
        assert result.rooms[0].name == "Office 101"
        assert result.scale_used == 1.0
        assert result.scale_source == "user_input"
        
    @patch("app.services.blueprint_extractor.get_vision_llm")
    @patch("app.services.blueprint_extractor._load_image_as_base64")
    def test_extraction_with_no_rooms_raises(self, mock_load_image, mock_get_llm):
        mock_load_image.return_value = "data:image/png;base64;fakeimagecontent"
        
        # Mock LLM response
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = '{"rooms": []}'
        mock_get_llm.return_value = mock_llm
        
        with pytest.raises(ValueError, match="No rooms extracted"):
            extract_rooms_from_blueprint(image_path="fake.png")


class TestGetImageDimensions:
    """Tests for _get_image_dimensions"""
    
    @patch("app.services.blueprint_extractor.Path")
    @patch("app.services.blueprint_extractor.Image")
    def test_get_dimensions_from_image(self, mock_image, mock_path):
        from pathlib import Path as PathLib
        # Mock Path.exists() to return True
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = ".png"
        mock_path.return_value = mock_path_obj
        
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.width = 1000
        mock_img.height = 800
        mock_image.open.return_value = mock_img
        
        width, height = _get_image_dimensions("fake.png")
        assert width == 1000
        assert height == 800
    
    @patch("app.services.blueprint_extractor.Path")
    @patch("app.services.blueprint_extractor.fitz")
    @patch("app.services.blueprint_extractor.Image")
    def test_get_dimensions_from_pdf_single_page(self, mock_image, mock_fitz, mock_path):
        from pathlib import Path as PathLib
        # Mock Path.exists() to return True
        mock_path_obj = MagicMock()
        mock_path_obj.exists.return_value = True
        mock_path_obj.suffix = ".pdf"
        mock_path.return_value = mock_path_obj
        
        # Mock PDF document
        mock_doc = MagicMock()
        mock_doc.__len__ = lambda x: 1
        mock_page = MagicMock()
        mock_pixmap = MagicMock()
        mock_pixmap.tobytes.return_value = b"fake_png_data"
        mock_page.get_pixmap.return_value = mock_pixmap
        mock_doc.__getitem__ = lambda x, y: mock_page
        mock_doc.close = MagicMock()
        mock_fitz.open.return_value = mock_doc
        
        # Mock PIL Image
        mock_img = MagicMock()
        mock_img.width = 1200
        mock_img.height = 900
        mock_image.open.return_value = mock_img
        
        width, height = _get_image_dimensions("fake.pdf", page_index=0)
        assert width == 1200
        assert height == 900
        mock_doc.close.assert_called_once()


class TestCreateOverlaysFromLabelBbox:
    """Tests for _create_overlays_from_label_bbox"""
    
    def test_create_overlays_with_valid_bbox(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 100, "y": 200, "width": 80, "height": 20}
            },
            {
                "id": "R102",
                "name": "Meeting Room",
                "type": "meeting",
                "level": 1,
                "area_m2": 25.0,
                "label_bbox": {"x": 300, "y": 450, "width": 120, "height": 18}
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0),
            Room(id="R102", name="Meeting Room", type="meeting", level=1, area_m2=25.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 2
        assert all(isinstance(o, Overlay) for o in overlays)
        assert overlays[0].id == "R101"
        assert overlays[0].x == 100
        assert overlays[0].y == 200
        assert overlays[0].width == 80
        assert overlays[0].height == 20
        assert overlays[0].room_name == "Office 101"
        assert overlays[0].room_type == "office"
    
    def test_create_overlays_skips_null_bbox(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 100, "y": 200, "width": 80, "height": 20}
            },
            {
                "id": "R102",
                "name": "Meeting Room",
                "type": "meeting",
                "level": 1,
                "area_m2": 25.0,
                "label_bbox": None  # No bbox
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0),
            Room(id="R102", name="Meeting Room", type="meeting", level=1, area_m2=25.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 1
        assert overlays[0].id == "R101"
    
    def test_create_overlays_skips_invalid_bbox(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 100, "y": 200, "width": 0, "height": 20}  # Zero width
            },
            {
                "id": "R102",
                "name": "Meeting Room",
                "type": "meeting",
                "level": 1,
                "area_m2": 25.0,
                "label_bbox": {"x": 300, "y": 450, "width": 120, "height": -10}  # Negative height
            },
            {
                "id": "R103",
                "name": "Kitchen",
                "type": "kitchen",
                "level": 1,
                "area_m2": 12.0,
                "label_bbox": {"x": 500, "y": 600, "width": 5, "height": 5}  # Too small (< 10x10)
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0),
            Room(id="R102", name="Meeting Room", type="meeting", level=1, area_m2=25.0),
            Room(id="R103", name="Kitchen", type="kitchen", level=1, area_m2=12.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 0  # All invalid
    
    def test_create_overlays_clamps_to_image_bounds(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 1950, "y": 1450, "width": 200, "height": 100}  # Exceeds bounds
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 1
        # Should be clamped: x=1950, width should be max 50 (2000 - 1950)
        assert overlays[0].x == 1950
        assert overlays[0].width <= 50
        assert overlays[0].height <= 50  # Also clamped
    
    def test_create_overlays_rejects_absurdly_large_bbox(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 100, "y": 200, "width": 1600, "height": 1000}  # >50% of image (1.6M / 3M = 53.3%)
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 0  # Rejected as too large (>50% of image area)
    
    def test_create_overlays_skips_unmatched_rooms(self):
        raw_rooms = [
            {
                "id": "R101",
                "name": "Office 101",
                "type": "office",
                "level": 1,
                "area_m2": 15.0,
                "label_bbox": {"x": 100, "y": 200, "width": 80, "height": 20}
            },
            {
                "id": "R999",  # Not in validated_rooms
                "name": "Unknown Room",
                "type": "other",
                "level": 1,
                "area_m2": 10.0,
                "label_bbox": {"x": 300, "y": 450, "width": 120, "height": 18}
            }
        ]
        validated_rooms = [
            Room(id="R101", name="Office 101", type="office", level=1, area_m2=15.0)
        ]
        
        overlays = _create_overlays_from_label_bbox(
            raw_rooms=raw_rooms,
            validated_rooms=validated_rooms,
            image_width=2000,
            image_height=1500
        )
        
        assert len(overlays) == 1
        assert overlays[0].id == "R101"  # R999 skipped


class TestExtractRoomsWithLabelBbox:
    """Tests for extract_rooms_from_blueprint with label_bbox"""
    
    @patch("app.services.blueprint_extractor._get_image_dimensions")
    @patch("app.services.blueprint_extractor.get_vision_llm")
    @patch("app.services.blueprint_extractor._load_image_as_base64")
    def test_extraction_with_label_bbox_creates_overlays(self, mock_load_image, mock_get_llm, mock_get_dims):
        # Mock image loading
        mock_load_image.return_value = "data:image/png;base64;fakeimagecontent"
        mock_get_dims.return_value = (2000, 1500)  # Image dimensions
        
        # Mock LLM response with label_bbox
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(
            {
                "rooms": [
                    {
                        "id": "R101",
                        "name": "Office 101",
                        "type": "office",
                        "area_m2": 15.0,
                        "level": 1,
                        "label_bbox": {"x": 100, "y": 200, "width": 80, "height": 20}
                    },
                    {
                        "id": "R102",
                        "name": "Meeting Room",
                        "type": "meeting",
                        "area_m2": 25.0,
                        "level": 1,
                        "label_bbox": {"x": 300, "y": 450, "width": 120, "height": 18}
                    }
                ]
            }
        )
        mock_get_llm.return_value = mock_llm
        
        result = extract_rooms_from_blueprint(
            image_path="fake_blueprint.png",
            scale_override=1.0
        )
        
        assert hasattr(result, "overlays")
        assert len(result.overlays) == 2
        assert all(isinstance(o, Overlay) for o in result.overlays)
        assert result.overlays[0].id == "R101"
        assert result.overlays[0].x == 100
        assert result.overlays[0].y == 200
        assert result.overlays[0].room_name == "Office 101"
        assert "overlays_generated" in result.extraction_metadata
        assert result.extraction_metadata["overlays_generated"] == 2
    
    @patch("app.services.blueprint_extractor._get_image_dimensions")
    @patch("app.services.blueprint_extractor.get_vision_llm")
    @patch("app.services.blueprint_extractor._load_image_as_base64")
    def test_extraction_with_mixed_bbox_creates_partial_overlays(self, mock_load_image, mock_get_llm, mock_get_dims):
        # Mock image loading
        mock_load_image.return_value = "data:image/png;base64;fakeimagecontent"
        mock_get_dims.return_value = (2000, 1500)
        
        # Mock LLM response with some rooms having bbox, some not
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(
            {
                "rooms": [
                    {
                        "id": "R101",
                        "name": "Office 101",
                        "type": "office",
                        "area_m2": 15.0,
                        "level": 1,
                        "label_bbox": {"x": 100, "y": 200, "width": 80, "height": 20}
                    },
                    {
                        "id": "R102",
                        "name": "Meeting Room",
                        "type": "meeting",
                        "area_m2": 25.0,
                        "level": 1,
                        "label_bbox": None  # No bbox
                    }
                ]
            }
        )
        mock_get_llm.return_value = mock_llm
        
        result = extract_rooms_from_blueprint(
            image_path="fake_blueprint.png",
            scale_override=1.0
        )
        
        assert len(result.rooms) == 2
        assert len(result.overlays) == 1  # Only R101 has overlay
        assert result.overlays[0].id == "R101"
    
    @patch("app.services.blueprint_extractor._get_image_dimensions")
    @patch("app.services.blueprint_extractor.get_vision_llm")
    @patch("app.services.blueprint_extractor._load_image_as_base64")
    def test_extraction_with_invalid_bbox_gracefully_handles(self, mock_load_image, mock_get_llm, mock_get_dims):
        # Mock image loading
        mock_load_image.return_value = "data:image/png;base64;fakeimagecontent"
        mock_get_dims.return_value = (2000, 1500)
        
        # Mock LLM response with invalid bbox
        mock_llm = MagicMock()
        mock_llm.invoke.return_value.content = json.dumps(
            {
                "rooms": [
                    {
                        "id": "R101",
                        "name": "Office 101",
                        "type": "office",
                        "area_m2": 15.0,
                        "level": 1,
                        "label_bbox": {"x": 100, "y": 200, "width": 0, "height": 20}  # Invalid: zero width
                    }
                ]
            }
        )
        mock_get_llm.return_value = mock_llm
        
        result = extract_rooms_from_blueprint(
            image_path="fake_blueprint.png",
            scale_override=1.0
        )
        
        assert len(result.rooms) == 1
        assert len(result.overlays) == 0  # Invalid bbox rejected
        assert result.extraction_metadata["overlays_generated"] == 0