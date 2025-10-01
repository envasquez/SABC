import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.helpers.logging.handlers import configure_handler_formatters, create_handlers
from core.helpers.logging.logger_setup import configure_root_logger, configure_security_logger


class SABCLogger:
    """Central logging configuration for SABC application."""

    def __init__(self, log_dir: str = "/tmp/sabc_logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True, parents=True)
        self._configured = False

    def configure_logging(
        self,
        log_level: str = "INFO",
        json_format: bool = True,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5,
    ) -> None:
        """Configure the logging system with handlers and formatters."""
        if self._configured:
            return

        # Configure root logger
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger = configure_root_logger(numeric_level)

        # Create all handlers
        console_handler, app_handler, security_handler, error_handler = create_handlers(
            self.log_dir,
            numeric_level,
            max_bytes,
            backup_count,
        )

        # Configure formatters
        configure_handler_formatters(
            console_handler,
            app_handler,
            security_handler,
            error_handler,
            json_format,
        )

        # Add handlers to root logger
        root_logger.addHandler(console_handler)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)

        # Configure security logger
        configure_security_logger(security_handler)

        self._configured = True

        # Log initialization
        logger = logging.getLogger(__name__)
        logger.info(
            "Logging system initialized",
            extra={
                "log_level": log_level,
                "json_format": json_format,
                "log_dir": str(self.log_dir),
            },
        )

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the sabc namespace."""
        if not self._configured:
            self.configure_logging()
        return logging.getLogger(f"sabc.{name}")

    def log_security_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        user_email: Optional[str] = None,
        ip_address: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        level: int = logging.INFO,
    ) -> None:
        """Log a security-related event with structured data."""
        if not self._configured:
            self.configure_logging()

        security_logger = logging.getLogger("sabc.security")

        extra = {
            "event_type": event_type,
            "user_id": user_id,
            "user_email": user_email,
            "ip_address": ip_address,
            "details": details or {},
        }

        security_logger.log(level, f"Security event: {event_type}", extra=extra)
