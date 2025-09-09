"""
Centralized logging configuration for SABC application.
Provides structured logging with rotation, security events, and audit trails.
"""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

# Log file paths
APP_LOG = LOG_DIR / "app.log"
SECURITY_LOG = LOG_DIR / "security.log"
AUDIT_LOG = LOG_DIR / "audit.log"
ERROR_LOG = LOG_DIR / "error.log"

# Log format for production (structured)
DETAILED_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
SIMPLE_FORMAT = "%(levelname)s - %(name)s - %(message)s"

# Determine if we're in development or production
IS_DEVELOPMENT = os.environ.get("ENVIRONMENT", "development") == "development"


def setup_logging(level: str = "INFO") -> None:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Convert string level to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    root_logger.handlers.clear()

    # Console handler (always active)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if IS_DEVELOPMENT else logging.INFO)
    console_formatter = logging.Formatter(SIMPLE_FORMAT if IS_DEVELOPMENT else DETAILED_FORMAT)
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handlers with rotation (5MB max, keep 10 backups)
    file_formatter = logging.Formatter(DETAILED_FORMAT)

    # Application log (all events)
    app_handler = logging.handlers.RotatingFileHandler(APP_LOG, maxBytes=5_242_880, backupCount=10)
    app_handler.setLevel(logging.DEBUG)
    app_handler.setFormatter(file_formatter)
    root_logger.addHandler(app_handler)

    # Error log (warnings and above)
    error_handler = logging.handlers.RotatingFileHandler(
        ERROR_LOG, maxBytes=5_242_880, backupCount=10
    )
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(file_formatter)
    root_logger.addHandler(error_handler)

    # Security logger
    security_logger = logging.getLogger("security")
    security_handler = logging.handlers.RotatingFileHandler(
        SECURITY_LOG,
        maxBytes=5_242_880,
        backupCount=20,  # Keep more security logs
    )
    security_handler.setFormatter(file_formatter)
    security_logger.addHandler(security_handler)
    security_logger.setLevel(logging.INFO)

    # Audit logger
    audit_logger = logging.getLogger("audit")
    audit_handler = logging.handlers.RotatingFileHandler(
        AUDIT_LOG,
        maxBytes=5_242_880,
        backupCount=20,  # Keep more audit logs
    )
    audit_handler.setFormatter(file_formatter)
    audit_logger.addHandler(audit_handler)
    audit_logger.setLevel(logging.INFO)

    # Suppress noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("watchfiles").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    user_email: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True,
    details: Optional[str] = None,
) -> None:
    """
    Log security-related events.

    Args:
        event_type: Type of security event (LOGIN, LOGOUT, ACCESS_DENIED, etc.)
        user_id: User ID if available
        user_email: User email if available
        ip_address: Client IP address
        success: Whether the action was successful
        details: Additional details about the event
    """
    security_logger = logging.getLogger("security")
    message = (
        f"EVENT={event_type} "
        f"USER_ID={user_id or 'ANONYMOUS'} "
        f"EMAIL={user_email or 'N/A'} "
        f"IP={ip_address or 'UNKNOWN'} "
        f"SUCCESS={success} "
        f"DETAILS={details or 'None'}"
    )

    if success:
        security_logger.info(message)
    else:
        security_logger.warning(message)


def log_audit_event(
    action: str,
    user_id: int,
    user_email: str,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    old_value: Optional[str] = None,
    new_value: Optional[str] = None,
    details: Optional[str] = None,
) -> None:
    """
    Log audit trail for admin actions.

    Args:
        action: Action performed (CREATE, UPDATE, DELETE)
        user_id: Admin user ID
        user_email: Admin user email
        target_type: Type of target (USER, TOURNAMENT, POLL, etc.)
        target_id: ID of the target object
        old_value: Previous value (for updates)
        new_value: New value (for updates)
        details: Additional details
    """
    audit_logger = logging.getLogger("audit")
    message = (
        f"ACTION={action} "
        f"ADMIN_ID={user_id} "
        f"ADMIN_EMAIL={user_email} "
        f"TARGET_TYPE={target_type or 'N/A'} "
        f"TARGET_ID={target_id or 'N/A'} "
        f"OLD_VALUE={old_value or 'N/A'} "
        f"NEW_VALUE={new_value or 'N/A'} "
        f"DETAILS={details or 'None'}"
    )
    audit_logger.info(message)


# Initialize logging when module is imported
setup_logging(os.environ.get("LOG_LEVEL", "INFO"))
