"""Logging helpers for password reset requests."""

from core.helpers.logging import SecurityEvent, get_logger, log_security_event

logger = get_logger("password_reset")


def log_reset_success(user_id: int, email: str, ip: str) -> None:
    """Log successful password reset request."""
    logger.info(
        f"Password reset requested and email sent to {email}",
        extra={"user_id": user_id, "email": email, "ip": ip},
    )
    log_security_event(
        SecurityEvent.PASSWORD_RESET_REQUESTED,
        user_id=user_id,
        user_email=email,
        ip_address=ip,
        details={"success": True},
    )


def log_reset_email_failed(user_id: int, email: str, ip: str) -> None:
    """Log failed email send for password reset."""
    logger.error(f"Failed to send password reset email to {email}")
    log_security_event(
        SecurityEvent.PASSWORD_RESET_REQUESTED,
        user_id=user_id,
        user_email=email,
        ip_address=ip,
        details={"success": False, "error": "email_send_failed"},
    )


def log_reset_rate_limited(user_id: int, email: str, ip: str) -> None:
    """Log rate limited password reset request."""
    logger.warning(f"Rate limited password reset request for {email}")
    log_security_event(
        SecurityEvent.PASSWORD_RESET_REQUESTED,
        user_id=user_id,
        user_email=email,
        ip_address=ip,
        details={"success": False, "error": "rate_limited"},
    )


def log_reset_user_not_found(email: str, ip: str) -> None:
    """Log password reset request for non-existent user."""
    logger.info(f"Password reset requested for non-existent email: {email}")
    log_security_event(
        SecurityEvent.PASSWORD_RESET_REQUESTED,
        user_id=None,
        user_email=email,
        ip_address=ip,
        details={"success": False, "error": "user_not_found"},
    )
