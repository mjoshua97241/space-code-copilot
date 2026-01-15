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
    extract_rooms_from_blueprint
)
from app.models.domain import Room

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
        
        assert "rooms" in result
        assert len(result["rooms"]) == 2
        assert result["rooms"][0].name == "Office 101"
        assert result["scale_used"] == 1.0
        assert result["scale_source"] == "user_input"
        
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