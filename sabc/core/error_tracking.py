# Error tracking and alerting system
import json
import logging
import sys
import traceback
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.core.cache import cache
from django.core.mail import mail_admins
from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class ErrorTracker:
    """
    Centralized error tracking and alerting system.
    Tracks errors, prevents spam, and sends appropriate notifications.
    """

    # Error severity levels
    SEVERITY_LOW = "low"
    SEVERITY_MEDIUM = "medium"
    SEVERITY_HIGH = "high"
    SEVERITY_CRITICAL = "critical"

    # Rate limiting for error notifications
    ERROR_RATE_LIMITS = {
        SEVERITY_LOW: 3600,  # 1 hour
        SEVERITY_MEDIUM: 1800,  # 30 minutes
        SEVERITY_HIGH: 600,  # 10 minutes
        SEVERITY_CRITICAL: 60,  # 1 minute
    }

    @classmethod
    def track_error(
        cls,
        error: Exception,
        request=None,
        severity: str = SEVERITY_MEDIUM,
        extra_data: Dict = None,
    ) -> str:
        """
        Track an error with context and severity.
        Returns error ID for reference.
        """
        error_id = cls._generate_error_id(error)

        error_data = {
            "id": error_id,
            "type": type(error).__name__,
            "message": str(error),
            "severity": severity,
            "timestamp": datetime.now().isoformat(),
            "traceback": traceback.format_exc(),
        }

        # Add request context if available
        if request:
            error_data.update(
                {
                    "request_path": request.path,
                    "request_method": request.method,
                    "user": str(request.user)
                    if hasattr(request, "user")
                    else "Anonymous",
                    "user_agent": request.META.get("HTTP_USER_AGENT", ""),
                    "ip_address": cls._get_client_ip(request),
                    "referer": request.META.get("HTTP_REFERER", ""),
                }
            )

        # Add extra data
        if extra_data:
            error_data["extra"] = extra_data

        # Store error data
        cls._store_error(error_data)

        # Send alerts if needed
        if cls._should_alert(error_id, severity):
            cls._send_alert(error_data)

        logger.error(
            f"Error tracked: {error_id} - {error_data['type']}: {error_data['message']}"
        )
        return error_id

    @classmethod
    def _generate_error_id(cls, error: Exception) -> str:
        """Generate a unique but consistent error ID."""
        import hashlib

        error_string = f"{type(error).__name__}:{str(error)}"
        return hashlib.md5(error_string.encode()).hexdigest()[:12]

    @classmethod
    def _get_client_ip(cls, request) -> str:
        """Get client IP from request."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")

    @classmethod
    def _store_error(cls, error_data: Dict):
        """Store error data for analysis."""
        try:
            # Store in cache for recent errors (last 24 hours)
            cache_key = f"error_recent:{error_data['id']}"
            cache.set(cache_key, error_data, 86400)

            # Maintain error count for rate limiting
            count_key = f"error_count:{error_data['id']}"
            current_count = cache.get(count_key, 0)
            cache.set(count_key, current_count + 1, 86400)

            # Store in file for persistent logging
            cls._log_to_file(error_data)

        except Exception as e:
            logger.warning(f"Failed to store error data: {e}")

    @classmethod
    def _log_to_file(cls, error_data: Dict):
        """Log error to file for persistent storage."""
        try:
            import os

            log_dir = os.path.join(settings.BASE_DIR, "logs")
            os.makedirs(log_dir, exist_ok=True)

            log_file = os.path.join(log_dir, "errors.jsonl")
            with open(log_file, "a") as f:
                f.write(json.dumps(error_data) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log error to file: {e}")

    @classmethod
    def _should_alert(cls, error_id: str, severity: str) -> bool:
        """Determine if an alert should be sent based on rate limiting."""
        if settings.DEBUG:
            return False  # No alerts in debug mode

        alert_key = f"error_alert:{error_id}"
        last_alert = cache.get(alert_key)

        if last_alert is None:
            # First occurrence, send alert
            rate_limit = cls.ERROR_RATE_LIMITS.get(severity, 3600)
            cache.set(alert_key, datetime.now().isoformat(), rate_limit)
            return True

        return False  # Already alerted recently

    @classmethod
    def _send_alert(cls, error_data: Dict):
        """Send error alert to administrators."""
        try:
            severity = error_data.get("severity", cls.SEVERITY_MEDIUM)
            subject = f"[SABC {severity.upper()}] {error_data['type']}: {error_data['message'][:100]}"

            message_parts = [
                f"Error ID: {error_data['id']}",
                f"Type: {error_data['type']}",
                f"Message: {error_data['message']}",
                f"Severity: {severity}",
                f"Timestamp: {error_data['timestamp']}",
            ]

            if "request_path" in error_data:
                message_parts.extend(
                    [
                        f"Path: {error_data['request_path']}",
                        f"Method: {error_data['request_method']}",
                        f"User: {error_data['user']}",
                        f"IP: {error_data['ip_address']}",
                    ]
                )

            message_parts.append(f"\nTraceback:\n{error_data['traceback']}")
            message = "\n".join(message_parts)

            mail_admins(subject, message, fail_silently=True)

        except Exception as e:
            logger.warning(f"Failed to send error alert: {e}")

    @classmethod
    def get_error_stats(cls, hours: int = 24) -> Dict[str, Any]:
        """Get error statistics for the specified time period."""
        # This is a simplified implementation
        # In production, you'd want to aggregate from persistent storage
        stats = {
            "total_errors": 0,
            "unique_errors": 0,
            "by_severity": {
                cls.SEVERITY_LOW: 0,
                cls.SEVERITY_MEDIUM: 0,
                cls.SEVERITY_HIGH: 0,
                cls.SEVERITY_CRITICAL: 0,
            },
            "top_errors": [],
        }

        return stats


class ErrorTrackingMiddleware(MiddlewareMixin):
    """
    Middleware to automatically track unhandled errors.
    """

    def process_exception(self, request, exception):
        """Track unhandled exceptions."""
        # Skip 404 errors (too noisy)
        if isinstance(exception, Http404):
            return None

        # Determine severity based on exception type
        severity = self._get_error_severity(exception)

        # Track the error
        ErrorTracker.track_error(
            exception,
            request=request,
            severity=severity,
            extra_data={"middleware": "ErrorTrackingMiddleware"},
        )

        # Don't suppress the exception, let Django handle it
        return None

    def _get_error_severity(self, exception: Exception) -> str:
        """Determine error severity based on exception type."""
        critical_errors = (
            ValueError,
            TypeError,
            AttributeError,
            KeyError,
            ImportError,
            MemoryError,
            OSError,
        )

        high_errors = (RuntimeError, LookupError, IndexError)

        if isinstance(exception, critical_errors):
            return ErrorTracker.SEVERITY_CRITICAL
        elif isinstance(exception, high_errors):
            return ErrorTracker.SEVERITY_HIGH
        else:
            return ErrorTracker.SEVERITY_MEDIUM


def track_custom_error(
    message: str,
    severity: str = ErrorTracker.SEVERITY_MEDIUM,
    extra_data: Dict = None,
    request=None,
):
    """
    Helper function to manually track custom errors.
    """

    class CustomError(Exception):
        pass

    error = CustomError(message)
    return ErrorTracker.track_error(error, request, severity, extra_data)


# Context manager for tracking errors in specific code blocks
class error_tracking:
    """Context manager for tracking errors in specific code blocks."""

    def __init__(
        self,
        operation: str,
        severity: str = ErrorTracker.SEVERITY_MEDIUM,
        request=None,
        extra_data: Dict = None,
    ):
        self.operation = operation
        self.severity = severity
        self.request = request
        self.extra_data = extra_data or {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            extra_data = self.extra_data.copy()
            extra_data["operation"] = self.operation

            ErrorTracker.track_error(
                exc_val,
                request=self.request,
                severity=self.severity,
                extra_data=extra_data,
            )

        # Don't suppress the exception
        return False
