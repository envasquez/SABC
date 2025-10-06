"""Password change logic for profile updates."""

from typing import Optional, Tuple

from core.db_schema import Angler, get_session
from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from core.helpers.password_validator import validate_password_strength
from routes.dependencies import bcrypt

logger = get_logger("auth.profile_update.password")


def handle_password_change(
    user: dict, current_password: str, new_password: str, confirm_password: str, ip_address: str
) -> Tuple[bool, Optional[str]]:
    """Handle password change validation and update.

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if not (current_password and new_password and confirm_password):
        return False, "All password fields are required to change password"

    # Validate new password strength
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        return False, error_message

    if new_password != confirm_password:
        return False, "New passwords do not match"

    with get_session() as session:
        current_user = session.query(Angler).filter(Angler.id == user["id"]).first()
        if not current_user or not current_user.password_hash:
            return False, "User not found"

        stored_password_hash = current_user.password_hash

        if not bcrypt.checkpw(
            current_password.encode("utf-8"), stored_password_hash.encode("utf-8")
        ):
            return False, "Current password is incorrect"

        new_password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        current_user.password_hash = new_password_hash

    log_security_event(
        SecurityEvent.PASSWORD_RESET_COMPLETED,
        user_id=user["id"],
        user_email=user["email"],
        ip_address=ip_address,
        details={"method": "profile_edit", "success": True},
    )

    logger.info("Password changed via profile", extra={"user_id": user["id"]})
    return True, None
