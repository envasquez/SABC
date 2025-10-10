import logging
from pathlib import Path
from typing import Any, Dict, Optional

from core.helpers.logging.handlers import configure_handler_formatters, create_handlers
from core.helpers.logging.logger_setup import configure_root_logger, configure_security_logger


class SABCLogger:
    def __init__(self, log_dir: str = "/tmp/sabc_logs"):  # nosec B108
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
        if self._configured:
            return
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger = configure_root_logger(numeric_level)
        console_handler, app_handler, security_handler, error_handler = create_handlers(
            self.log_dir,
            numeric_level,
            max_bytes,
            backup_count,
        )
        configure_handler_formatters(
            console_handler,
            app_handler,
            security_handler,
            error_handler,
            json_format,
        )
        root_logger.addHandler(console_handler)
        root_logger.addHandler(app_handler)
        root_logger.addHandler(error_handler)
        configure_security_logger(security_handler)

        self._configured = True
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
