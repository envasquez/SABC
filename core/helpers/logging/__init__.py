import logging
from typing import Any, Dict, Optional

from core.helpers.logging.config import SABCLogger
from core.helpers.logging.security import SecurityEvent

sabc_logger = SABCLogger()


def get_logger(name: str) -> logging.Logger:
    return sabc_logger.get_logger(name)


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    level: int = logging.INFO,
) -> None:
    sabc_logger.log_security_event(event_type, user_id, user_email, ip_address, details, level)


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    sabc_logger.configure_logging(log_level, json_format)


__all__ = ["SecurityEvent", "get_logger", "log_security_event", "configure_logging"]
