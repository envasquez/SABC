"""Unit tests for response helper functions."""

from fastapi.responses import RedirectResponse

from core.helpers.response import error_redirect, success_redirect


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
