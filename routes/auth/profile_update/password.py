"""Password change logic for profile updates."""

from typing import Optional, Tuple

from core.helpers.logging import SecurityEvent, get_logger, log_security_event
from routes.dependencies import bcrypt, db

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

    if len(new_password) < 8:
        return False, "New password must be at least 8 characters long"

    if new_password != confirm_password:
        return False, "New passwords do not match"

    current_user = db(
        "SELECT password as password_hash FROM anglers WHERE id = :user_id", {"user_id": user["id"]}
    )
    if not current_user:
        return False, "User not found"

    stored_password_hash = current_user[0][0]

    if not bcrypt.checkpw(current_password.encode("utf-8"), stored_password_hash.encode("utf-8")):
        return False, "Current password is incorrect"

    new_password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode(
        "utf-8"
    )

    db(
        "UPDATE anglers SET password = :password WHERE id = :user_id",
        {"password": new_password_hash, "user_id": user["id"]},
    )

    log_security_event(
        SecurityEvent.PASSWORD_RESET_COMPLETED,
        user_id=user["id"],
        user_email=user["email"],
        ip_address=ip_address,
        details={"method": "profile_edit", "success": True},
    )

    logger.info("Password changed via profile", extra={"user_id": user["id"]})
    return True, None
