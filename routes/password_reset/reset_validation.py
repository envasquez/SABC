from typing import Optional

from core.helpers.password_validator import validate_password_strength

ERROR_PASSWORDS_DONT_MATCH = "Passwords do not match. Please try again."
ERROR_INVALID_TOKEN = (
    "This password reset link is invalid or has expired. Please request a new one."
)
ERROR_RESET_FAILED = "Sorry, something went wrong while resetting your password. Please try again."


def validate_password_reset(password: str, password_confirm: str) -> Optional[str]:
    # Validate password strength
    is_valid, error_message = validate_password_strength(password)
    if not is_valid:
        return error_message

    if password != password_confirm:
        return ERROR_PASSWORDS_DONT_MATCH

    return None
