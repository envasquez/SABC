"""Unit tests for email service."""

import smtplib
from unittest.mock import MagicMock, Mock, patch

from core.email.service import send_password_reset_email


class TestSendPasswordResetEmail:
    """Tests for send_password_reset_email function."""

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_sends_email_successfully(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test successful email sending."""
        # Setup mocks
        mock_generate.return_value = (
            "Reset Your Password",
            "Text body",
            "<html>HTML body</html>",
        )
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        # Call function
        result = send_password_reset_email("user@test.com", "Test User", "token123")

        # Assertions
        assert result is True
        mock_generate.assert_called_once_with("Test User", "token123")
        mock_smtp.starttls.assert_called_once()
        mock_smtp.login.assert_called_once()
        mock_smtp.send_message.assert_called_once()

    @patch("core.email.service.SMTP_USERNAME", None)
    @patch("core.email.service.SMTP_PASSWORD", "password")
    def test_fails_without_smtp_username(self):
        """Test returns False when SMTP username not configured."""
        result = send_password_reset_email("user@test.com", "User", "token")
        assert result is False

    @patch("core.email.service.SMTP_USERNAME", "username")
    @patch("core.email.service.SMTP_PASSWORD", None)
    def test_fails_without_smtp_password(self):
        """Test returns False when SMTP password not configured."""
        result = send_password_reset_email("user@test.com", "User", "token")
        assert result is False

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_handles_smtp_connection_error(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test handles SMTP connection errors gracefully."""
        mock_generate.return_value = ("Subject", "Text", "HTML")
        mock_smtp_class.side_effect = smtplib.SMTPException("Connection failed")

        result = send_password_reset_email("user@test.com", "User", "token")

        assert result is False

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_handles_smtp_auth_error(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test handles SMTP authentication errors."""
        mock_generate.return_value = ("Subject", "Text", "HTML")
        mock_smtp = MagicMock()
        mock_smtp.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Auth failed")
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        result = send_password_reset_email("user@test.com", "User", "token")

        assert result is False

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_creates_mime_message_correctly(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test MIME message structure is correct."""
        mock_generate.return_value = (
            "Password Reset",
            "Plain text body",
            "<html>HTML body</html>",
        )
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        send_password_reset_email("recipient@test.com", "User", "token")

        # Check that send_message was called with a message
        sent_msg = mock_smtp.send_message.call_args[0][0]
        assert sent_msg["Subject"] == "Password Reset"
        assert sent_msg["To"] == "recipient@test.com"
        assert "From" in sent_msg

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_uses_starttls_for_security(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test that STARTTLS is used for secure connection."""
        mock_generate.return_value = ("Subject", "Text", "HTML")
        mock_smtp = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_smtp

        send_password_reset_email("user@test.com", "User", "token")

        # Verify STARTTLS is called before login
        calls = [call[0] for call in mock_smtp.method_calls]
        starttls_index = next(i for i, call in enumerate(calls) if "starttls" in str(call))
        login_index = next(i for i, call in enumerate(calls) if "login" in str(call))
        assert starttls_index < login_index

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_handles_template_generation_error(self, mock_generate: Mock, mock_smtp_class: Mock):
        """Test handles errors in template generation."""
        mock_generate.side_effect = Exception("Template error")

        result = send_password_reset_email("user@test.com", "User", "token")

        assert result is False

    @patch("core.email.service.SMTP_USERNAME", "test@example.com")
    @patch("core.email.service.SMTP_PASSWORD", "test_password")
    @patch("core.email.service.smtplib.SMTP")
    @patch("core.email.service.generate_reset_email_content")
    def test_smtp_connection_is_closed_after_sending(
        self, mock_generate: Mock, mock_smtp_class: Mock
    ):
        """Test SMTP connection is properly closed (context manager)."""
        mock_generate.return_value = ("Subject", "Text", "HTML")
        mock_smtp = MagicMock()
        mock_smtp_context = MagicMock()
        mock_smtp_context.__enter__.return_value = mock_smtp
        mock_smtp_class.return_value = mock_smtp_context

        send_password_reset_email("user@test.com", "User", "token")

        # Verify context manager was used (enter and exit called)
        mock_smtp_context.__enter__.assert_called_once()
        mock_smtp_context.__exit__.assert_called_once()
