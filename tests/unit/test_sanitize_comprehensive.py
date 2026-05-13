"""Comprehensive sanitize helper tests."""

from core.helpers.sanitize import (
    safe_json_dumps,
    sanitize_event_data,
    sanitize_for_json,
    sanitize_html,
    sanitize_iframe,
    sanitize_lakes_data,
)


class TestSanitizeIframe:
    """Lake/ramp Google Maps iframes must render through sanitize_iframe."""

    def test_double_quoted_attributes(self):
        """Iframes copy-pasted from Google Maps with double quotes pass through."""
        src = "https://www.google.com/maps/embed?pb=!1m18!1m12"
        raw = f'<iframe src="{src}" width="600" height="450"></iframe>'
        out = sanitize_iframe(raw)
        assert src in out
        assert out.startswith("<iframe")

    def test_single_quoted_attributes(self):
        """Production seed data ships single-quoted iframes — must still match.

        Regression: scripts/lakes_production.json stores iframes like
        <iframe src='https://www.google.com/maps/embed?pb=...' width='100%'>.
        The original regex only accepted double quotes, which made every
        lake/ramp map silently render as empty on the home page.
        """
        src = "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3"
        raw = f"<iframe src='{src}' width='100%' height='100%'></iframe>"
        out = sanitize_iframe(raw)
        assert src in out
        assert out.startswith("<iframe")

    def test_non_google_src_rejected(self):
        """Non-Google iframes get stripped (security contract)."""
        raw = '<iframe src="https://evil.example.com/xss"></iframe>'
        assert sanitize_iframe(raw) == ""

    def test_empty_input_returns_empty(self):
        assert sanitize_iframe("") == ""
        assert sanitize_iframe("   ") == ""


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
