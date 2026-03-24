"""Unit tests for response helper functions."""

from fastapi.responses import RedirectResponse

from core.helpers.response import (
    error_redirect,
    get_safe_redirect_url,
    is_safe_redirect_url,
    success_redirect,
)


class TestResponseHelpers:
    """Test response helper functions."""

    def test_success_redirect_default_code(self):
        """Test success redirect uses 303 by default."""
        result = success_redirect("/home", "Success")
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303

    def test_error_redirect_default_code(self):
        """Test error redirect uses 303 by default."""
        result = error_redirect("/back", "Error")
        assert isinstance(result, RedirectResponse)
        assert result.status_code == 303


class TestSafeRedirectUrl:
    """Test URL redirection validation functions."""

    def test_is_safe_redirect_url_valid_paths(self):
        """Test that valid relative paths are accepted."""
        assert is_safe_redirect_url("/") is True
        assert is_safe_redirect_url("/admin") is True
        assert is_safe_redirect_url("/admin/events") is True
        assert is_safe_redirect_url("/profile?tab=settings") is True
        assert is_safe_redirect_url("/path/to/page#section") is True

    def test_is_safe_redirect_url_protocol_relative(self):
        """Test that protocol-relative URLs are rejected."""
        assert is_safe_redirect_url("//evil.com") is False
        assert is_safe_redirect_url("//evil.com/path") is False
        assert is_safe_redirect_url("//") is False

    def test_is_safe_redirect_url_absolute_urls(self):
        """Test that absolute URLs with schemes are rejected."""
        assert is_safe_redirect_url("http://evil.com") is False
        assert is_safe_redirect_url("https://evil.com") is False
        assert is_safe_redirect_url("https://evil.com/path") is False
        assert is_safe_redirect_url("ftp://evil.com") is False

    def test_is_safe_redirect_url_javascript(self):
        """Test that javascript: URLs are rejected."""
        assert is_safe_redirect_url("javascript:alert(1)") is False
        assert is_safe_redirect_url("javascript:void(0)") is False

    def test_is_safe_redirect_url_relative_paths_no_slash(self):
        """Test that relative paths without leading slash are rejected."""
        assert is_safe_redirect_url("admin") is False
        assert is_safe_redirect_url("path/to/page") is False
        assert is_safe_redirect_url("..") is False

    def test_is_safe_redirect_url_empty_and_none(self):
        """Test that empty/None values are rejected."""
        assert is_safe_redirect_url("") is False
        assert is_safe_redirect_url(None) is False  # type: ignore[arg-type]

    def test_is_safe_redirect_url_whitespace(self):
        """Test that whitespace is handled correctly."""
        assert is_safe_redirect_url("  /admin  ") is True
        assert is_safe_redirect_url("   ") is False

    def test_is_safe_redirect_url_embedded_scheme(self):
        """Test that embedded schemes in path are rejected."""
        assert is_safe_redirect_url("/redirect?url=http://evil.com") is False

    def test_get_safe_redirect_url_valid(self):
        """Test get_safe_redirect_url returns valid URLs."""
        assert get_safe_redirect_url("/admin") == "/admin"
        assert get_safe_redirect_url("/profile?tab=settings") == "/profile?tab=settings"

    def test_get_safe_redirect_url_invalid_returns_default(self):
        """Test get_safe_redirect_url returns default for invalid URLs."""
        assert get_safe_redirect_url("https://evil.com") == "/"
        assert get_safe_redirect_url("//evil.com") == "/"
        assert get_safe_redirect_url("") == "/"

    def test_get_safe_redirect_url_custom_default(self):
        """Test get_safe_redirect_url with custom default."""
        assert get_safe_redirect_url("https://evil.com", default="/admin/events") == "/admin/events"
        assert get_safe_redirect_url("", default="/home") == "/home"
