"""Comprehensive sanitize helper tests."""

from core.helpers.sanitize import (
    safe_json_dumps,
    sanitize_event_data,
    sanitize_for_json,
    sanitize_html,
    sanitize_lakes_data,
)


class TestSanitize:
    """Test sanitization functions."""

    def test_sanitize_html_basic(self):
        """Test basic HTML sanitization."""
        result = sanitize_html("<p>Test</p>")
        assert "Test" in result

    def test_sanitize_html_script_removal(self):
        """Test script tag removal."""
        result = sanitize_html("<p>Safe</p><script>alert('xss')</script>")
        assert "<script>" not in result
        assert "Safe" in result

    def test_sanitize_for_json(self):
        """Test JSON sanitization."""
        test_dict = {"key": "value<script>", "num": 123}
        result = sanitize_for_json(test_dict)
        assert isinstance(result, dict)

    def test_safe_json_dumps(self):
        """Test safe JSON dumps."""
        test_data = {"test": "data"}
        result = safe_json_dumps(test_data)
        assert isinstance(result, str)
        assert "test" in result

    def test_sanitize_lakes_data(self):
        """Test lakes data sanitization."""
        lakes_data = [{"id": 1, "name": "Lake<script>", "display_name": "Display"}]
        result = sanitize_lakes_data(lakes_data)
        assert isinstance(result, list)

    def test_sanitize_event_data(self):
        """Test event data sanitization."""
        event_data = {
            "name": "Event<script>",
            "description": "Desc",
            "date": "2024-01-01",
        }
        result = sanitize_event_data(event_data)
        assert isinstance(result, dict)
