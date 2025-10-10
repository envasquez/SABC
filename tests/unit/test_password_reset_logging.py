"""Unit tests for password reset logging functions."""

from unittest.mock import patch

from routes.password_reset.request_logging import (
    log_reset_email_failed,
    log_reset_rate_limited,
    log_reset_success,
    log_reset_user_not_found,
)


class TestPasswordResetLogging:
    """Test suite for password reset logging functions."""

    @patch("routes.password_reset.request_logging.logger")
    @patch("routes.password_reset.request_logging.log_security_event")
    def test_log_reset_success(self, mock_log_security, mock_logger):
        """Test log_reset_success logs success message."""
        log_reset_success(user_id=123, email="test@example.com", ip="192.168.1.1")

        # Verify logger called
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        assert "test@example.com" in call_args[0][0]

        # Verify security event logged
        assert mock_log_security.called
        call_kwargs = mock_log_security.call_args.kwargs
        assert call_kwargs["user_id"] == 123
        assert call_kwargs["user_email"] == "test@example.com"
        assert call_kwargs["ip_address"] == "192.168.1.1"
        assert call_kwargs["details"]["success"] is True

    @patch("routes.password_reset.request_logging.logger")
    @patch("routes.password_reset.request_logging.log_security_event")
    def test_log_reset_email_failed(self, mock_log_security, mock_logger):
        """Test log_reset_email_failed logs error message."""
        log_reset_email_failed(user_id=456, email="fail@example.com", ip="10.0.0.1")

        # Verify logger called with error
        assert mock_logger.error.called
        call_args = mock_logger.error.call_args
        assert "fail@example.com" in call_args[0][0]

        # Verify security event logged with failure
        assert mock_log_security.called
        call_kwargs = mock_log_security.call_args.kwargs
        assert call_kwargs["user_id"] == 456
        assert call_kwargs["user_email"] == "fail@example.com"
        assert call_kwargs["details"]["success"] is False
        assert call_kwargs["details"]["error"] == "email_send_failed"

    @patch("routes.password_reset.request_logging.logger")
    @patch("routes.password_reset.request_logging.log_security_event")
    def test_log_reset_rate_limited(self, mock_log_security, mock_logger):
        """Test log_reset_rate_limited logs warning message."""
        log_reset_rate_limited(user_id=789, email="rate@example.com", ip="172.16.0.1")

        # Verify logger called with warning
        assert mock_logger.warning.called
        call_args = mock_logger.warning.call_args
        assert "rate@example.com" in call_args[0][0]
        assert "Rate limited" in call_args[0][0]

        # Verify security event logged with rate limit error
        assert mock_log_security.called
        call_kwargs = mock_log_security.call_args.kwargs
        assert call_kwargs["user_id"] == 789
        assert call_kwargs["user_email"] == "rate@example.com"
        assert call_kwargs["details"]["success"] is False
        assert call_kwargs["details"]["error"] == "rate_limited"

    @patch("routes.password_reset.request_logging.logger")
    @patch("routes.password_reset.request_logging.log_security_event")
    def test_log_reset_user_not_found(self, mock_log_security, mock_logger):
        """Test log_reset_user_not_found logs non-existent email."""
        log_reset_user_not_found(email="nobody@example.com", ip="192.0.2.1")

        # Verify logger called
        assert mock_logger.info.called
        call_args = mock_logger.info.call_args
        assert "nobody@example.com" in call_args[0][0]
        assert "non-existent" in call_args[0][0]

        # Verify security event logged with user_id=None
        assert mock_log_security.called
        call_kwargs = mock_log_security.call_args.kwargs
        assert call_kwargs["user_id"] is None
        assert call_kwargs["user_email"] == "nobody@example.com"
        assert call_kwargs["details"]["success"] is False
        assert call_kwargs["details"]["error"] == "user_not_found"
