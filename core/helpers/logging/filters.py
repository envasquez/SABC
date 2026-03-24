"""Logging filters for sensitive data redaction."""

import logging
import re
from typing import Any, List, Pattern, Set


class SensitiveDataFilter(logging.Filter):
    """
    Filter that redacts sensitive data from log records.

    This filter automatically scrubs passwords, API keys, tokens, and other
    sensitive information from log messages and extra fields before they
    are written to log files or sent to external services.

    Usage:
        handler.addFilter(SensitiveDataFilter())
    """

    # Patterns to match sensitive data in log messages
    # Each pattern captures the sensitive value in group 1
    PATTERNS: List[Pattern[str]] = [
        # password=value, password: value, "password": "value"
        re.compile(
            r'(password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # api_key=value, api-key=value
        re.compile(
            r'(api[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # secret=value, secret_key=value
        re.compile(
            r'(secret[_-]?key?)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # token=value, auth_token=value, access_token=value
        re.compile(
            r'((?:auth[_-]?|access[_-]?|refresh[_-]?)?token)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # authorization: Bearer xxx
        re.compile(
            r'(authorization)["\']?\s*[:=]\s*["\']?(bearer\s+\S+|basic\s+\S+)',
            re.IGNORECASE,
        ),
        # credential=value
        re.compile(
            r'(credential)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # session_id, session_key
        re.compile(
            r'(session[_-]?(?:id|key))["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
        # private_key, encryption_key
        re.compile(
            r'((?:private|encryption)[_-]?key)["\']?\s*[:=]\s*["\']?([^"\'}\s,;\]]+)',
            re.IGNORECASE,
        ),
    ]

    # Keys in extra dict that should always be redacted
    SENSITIVE_KEYS: Set[str] = {
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "api_key",
        "apikey",
        "auth",
        "authorization",
        "credential",
        "private_key",
        "session_id",
    }

    REDACTED = "[REDACTED]"

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Filter the log record by redacting sensitive data.

        Args:
            record: The log record to filter

        Returns:
            True (always allow the record through after redaction)
        """
        # Redact the message
        record.msg = self._redact_message(record.msg)

        # Redact args if present (for % formatting)
        if record.args:
            record.args = self._redact_args(record.args)

        # Redact extra fields
        self._redact_extra_fields(record)

        return True

    def _redact_message(self, msg: Any) -> Any:
        """Redact sensitive patterns from a log message."""
        if not isinstance(msg, str):
            return msg

        result = msg
        for pattern in self.PATTERNS:
            # Replace the captured sensitive value with REDACTED
            # Keep the key name for context (e.g., "password=[REDACTED]")
            result = pattern.sub(rf"\1={self.REDACTED}", result)

        return result

    def _redact_args(self, args: Any) -> Any:
        """Redact sensitive data from format arguments."""
        if isinstance(args, dict):
            return {
                k: self.REDACTED if self._is_sensitive_key(k) else self._redact_value(v)
                for k, v in args.items()
            }
        elif isinstance(args, (list, tuple)):
            redacted = [self._redact_value(arg) for arg in args]
            return tuple(redacted) if isinstance(args, tuple) else redacted
        return args

    def _redact_value(self, value: Any) -> Any:
        """Redact a single value if it's a string containing sensitive data."""
        if isinstance(value, str):
            return self._redact_message(value)
        return value

    def _redact_extra_fields(self, record: logging.LogRecord) -> None:
        """Redact sensitive keys in the record's extra fields."""
        for key in list(record.__dict__.keys()):
            if self._is_sensitive_key(key):
                setattr(record, key, self.REDACTED)
            elif isinstance(getattr(record, key, None), str):
                # Also check string values for sensitive patterns
                value = getattr(record, key)
                redacted = self._redact_message(value)
                if redacted != value:
                    setattr(record, key, redacted)

    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key name indicates sensitive data."""
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)


def create_sensitive_data_filter() -> SensitiveDataFilter:
    """Factory function to create a SensitiveDataFilter instance."""
    return SensitiveDataFilter()
