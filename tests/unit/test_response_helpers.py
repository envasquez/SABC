"""Unit tests for response helper functions."""

from unittest.mock import MagicMock

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.response import (
    error_redirect,
    get_client_ip,
    json_error,
    json_success,
    sanitize_error_message,
    set_user_session,
    success_redirect,
)


class TestRedirectHelpers:
    """Test suite for redirect helper functions."""

    def test_error_redirect_returns_redirect_response(self):
        """Test error_redirect returns RedirectResponse with error query param."""
        result = error_redirect("/dashboard", "Something went wrong")

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        # URL encoding converts spaces to %20
        assert result.headers["location"] == "/dashboard?error=Something%20went%20wrong"

    def test_error_redirect_custom_status_code(self):
        """Test error_redirect accepts custom status code."""
        result = error_redirect("/dashboard", "Error", status_code=303)

        assert result.status_code == 303

    def test_error_redirect_encodes_special_characters(self):
        """Test error_redirect properly handles special characters in message."""
        result = error_redirect("/home", "Invalid value: test@example.com")

        assert "error=" in result.headers["location"]
        assert "/home?" in result.headers["location"]

    def test_success_redirect_returns_redirect_response(self):
        """Test success_redirect returns RedirectResponse with success query param."""
        result = success_redirect("/dashboard", "Operation successful")

        assert isinstance(result, RedirectResponse)
        assert result.status_code == 302
        # URL encoding converts spaces to %20
        assert result.headers["location"] == "/dashboard?success=Operation%20successful"

    def test_success_redirect_custom_status_code(self):
        """Test success_redirect accepts custom status code."""
        result = success_redirect("/home", "Done", status_code=303)

        assert result.status_code == 303


class TestJSONHelpers:
    """Test suite for JSON response helper functions."""

    def test_json_error_returns_json_response(self):
        """Test json_error returns JSONResponse with error message."""
        result = json_error("Invalid input")

        assert isinstance(result, JSONResponse)
        assert result.status_code == 400
        # Check body content
        assert result.body == b'{"error":"Invalid input"}'

    def test_json_error_custom_status_code(self):
        """Test json_error accepts custom status code."""
        result = json_error("Not found", status_code=404)

        assert result.status_code == 404

    def test_json_success_basic(self):
        """Test json_success returns success response."""
        result = json_success()

        assert isinstance(result, JSONResponse)
        assert result.status_code == 200
        assert result.body == b'{"success":true}'

    def test_json_success_with_data(self):
        """Test json_success includes data when provided."""
        result = json_success(data={"user_id": 123, "name": "Test"})

        assert result.status_code == 200
        assert b'"success":true' in result.body
        assert b'"data":{' in result.body
        assert b'"user_id":123' in result.body

    def test_json_success_with_message(self):
        """Test json_success includes message when provided."""
        result = json_success(message="Operation completed")

        assert b'"success":true' in result.body
        assert b'"message":"Operation completed"' in result.body

    def test_json_success_with_data_and_message(self):
        """Test json_success includes both data and message."""
        result = json_success(
            data={"count": 5},
            message="Items retrieved",
        )

        assert b'"success":true' in result.body
        assert b'"data":{' in result.body
        assert b'"message":"Items retrieved"' in result.body

    def test_json_success_custom_status_code(self):
        """Test json_success accepts custom status code."""
        result = json_success(status_code=201)

        assert result.status_code == 201


class TestUtilityHelpers:
    """Test suite for utility helper functions."""

    def test_get_client_ip_returns_client_host(self):
        """Test get_client_ip returns client host from request."""
        request = MagicMock(spec=Request)
        request.client.host = "192.168.1.100"

        result = get_client_ip(request)

        assert result == "192.168.1.100"

    def test_get_client_ip_handles_missing_client(self):
        """Test get_client_ip returns 'unknown' when client is None."""
        request = MagicMock(spec=Request)
        request.client = None

        result = get_client_ip(request)

        assert result == "unknown"

    def test_set_user_session_clears_and_sets_user_id(self):
        """Test set_user_session clears old session and sets new user_id."""
        request = MagicMock(spec=Request)
        # Create a mock dict with a clear method
        mock_session = MagicMock()
        mock_session.__setitem__ = MagicMock()
        request.session = mock_session

        set_user_session(request, 42)

        # Should have called clear()
        mock_session.clear.assert_called_once()
        # Should have set user_id
        mock_session.__setitem__.assert_called_once_with("user_id", 42)

    def test_sanitize_error_message_returns_generic_message(self):
        """Test sanitize_error_message returns generic message."""
        error = ValueError("Database connection string contains password: secret123")

        result = sanitize_error_message(error)

        # Should not contain sensitive info
        assert "secret123" not in result
        # Should return generic message
        assert result == "An error occurred"

    def test_sanitize_error_message_custom_generic_message(self):
        """Test sanitize_error_message accepts custom generic message."""
        error = Exception("Internal error")

        result = sanitize_error_message(error, generic_message="Operation failed")

        assert result == "Operation failed"

    def test_sanitize_error_message_logs_actual_error(self, caplog):
        """Test sanitize_error_message logs the actual error."""
        import logging

        caplog.set_level(logging.ERROR)
        error = RuntimeError("Actual detailed error message")

        result = sanitize_error_message(error)

        # Should log the actual error
        assert any("Actual detailed error message" in record.message for record in caplog.records)
        # But return generic message
        assert result == "An error occurred"
