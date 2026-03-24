"""Tests for the SensitiveDataFilter logging filter."""

import logging

import pytest

from core.helpers.logging.filters import SensitiveDataFilter


class TestSensitiveDataFilter:
    """Test suite for SensitiveDataFilter."""

    @pytest.fixture
    def log_filter(self) -> SensitiveDataFilter:
        """Create a fresh filter instance for each test."""
        return SensitiveDataFilter()

    @pytest.fixture
    def log_record(self) -> logging.LogRecord:
        """Create a basic log record for testing."""
        return logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )

    def test_redacts_password_in_message(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Password values should be redacted from log messages."""
        log_record.msg = "Login: email@test.com / password=secret123"
        log_filter.filter(log_record)
        assert "secret123" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_redacts_api_key_in_message(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """API keys should be redacted from log messages."""
        log_record.msg = "Request with api_key=abc123xyz"
        log_filter.filter(log_record)
        assert "abc123xyz" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_redacts_token_in_message(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Tokens should be redacted from log messages."""
        log_record.msg = "Using auth_token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        log_filter.filter(log_record)
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_redacts_authorization_header(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Authorization headers should be redacted."""
        log_record.msg = "Header: authorization=Bearer abc123token"
        log_filter.filter(log_record)
        assert "abc123token" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_redacts_secret_key(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Secret keys should be redacted."""
        log_record.msg = "Config: secret_key=mysupersecretkey123"
        log_filter.filter(log_record)
        assert "mysupersecretkey123" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_redacts_json_style_password(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """JSON-style password fields should be redacted."""
        log_record.msg = '{"username": "admin", "password": "secret123"}'
        log_filter.filter(log_record)
        assert "secret123" not in log_record.msg
        assert "[REDACTED]" in log_record.msg

    def test_preserves_non_sensitive_data(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Non-sensitive data should not be modified."""
        log_record.msg = "User john@example.com logged in successfully"
        original_msg = log_record.msg
        log_filter.filter(log_record)
        assert log_record.msg == original_msg

    def test_redacts_sensitive_extra_fields(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Extra fields with sensitive keys should be redacted."""
        log_record.password = "secret123"  # type: ignore[attr-defined]
        log_record.api_key = "abc123"  # type: ignore[attr-defined]
        log_record.username = "admin"  # type: ignore[attr-defined]
        log_filter.filter(log_record)
        assert log_record.password == "[REDACTED]"  # type: ignore[attr-defined]
        assert log_record.api_key == "[REDACTED]"  # type: ignore[attr-defined]
        assert log_record.username == "admin"  # type: ignore[attr-defined]

    def test_case_insensitive_matching(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Pattern matching should be case-insensitive."""
        log_record.msg = "PASSWORD=secret123 API_KEY=abc123"
        log_filter.filter(log_record)
        assert "secret123" not in log_record.msg
        assert "abc123" not in log_record.msg

    def test_always_returns_true(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Filter should always return True (allow record through)."""
        result = log_filter.filter(log_record)
        assert result is True

    def test_handles_non_string_message(
        self, log_filter: SensitiveDataFilter, log_record: logging.LogRecord
    ) -> None:
        """Non-string messages should be handled gracefully."""
        log_record.msg = 12345  # type: ignore[assignment]
        result = log_filter.filter(log_record)
        assert result is True
        assert log_record.msg == 12345
