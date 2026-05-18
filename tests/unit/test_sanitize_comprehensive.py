"""Comprehensive sanitize helper tests."""

from core.helpers.sanitize import (
    sanitize_html,
    sanitize_iframe,
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

    def test_sanitize_html_removes_javascript_protocol(self):
        """Test that javascript: protocol is stripped from plain text."""
        result = sanitize_html("javascript:alert(1)")
        assert "javascript:" not in result.lower()
