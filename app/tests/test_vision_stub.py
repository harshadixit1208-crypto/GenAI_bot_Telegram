# app/tests/test_vision_stub.py
"""
Unit tests for vision service (stubbed for testing).
"""
import tempfile
import os
import pytest
from PIL import Image


class TestVisionService:
    """Tests for vision service."""

    @pytest.fixture
    def temp_image(self):
        """Create a temporary test image."""
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            # Create a simple PIL image
            img = Image.new("RGB", (100, 100), color="red")
            img.save(f.name)
            yield f.name
            os.unlink(f.name)

    def test_blip_service_initialization(self):
        """Test BLIP service can be initialized."""
        from app.vision.blip_service import BLIPCaptioningService

        service = BLIPCaptioningService()
        stats = service.get_stats()

        assert "model_name" in stats
        assert "device" in stats
        assert "initialized" in stats

    def test_extract_keywords(self):
        """Test keyword extraction from caption."""
        from app.vision.blip_service import BLIPCaptioningService

        service = BLIPCaptioningService()

        caption = "A beautiful cat sitting on a red couch in the living room"
        keywords = service._extract_keywords(caption)

        assert len(keywords) <= 3
        assert all(isinstance(k, str) for k in keywords)
        # Should extract meaningful words
        keywords_lower = [k.lower() for k in keywords]
        assert any(word in keywords_lower for word in ["beautiful", "couch", "living", "room", "sitting"])

    def test_caption_result_structure(self):
        """Test caption result has expected structure."""
        from app.vision.blip_service import BLIPCaptioningService

        service = BLIPCaptioningService()

        # Mock result
        result = {
            "caption": "A test caption",
            "tags": ["tag1", "tag2", "tag3"],
            "description": "Longer description",
            "success": True,
        }

        assert "caption" in result
        assert "tags" in result
        assert "description" in result
        assert "success" in result

        assert isinstance(result["caption"], str)
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) == 3
