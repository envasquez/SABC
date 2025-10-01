from typing import Optional

ERROR_PASSWORD_TOO_SHORT = "Password must be at least 8 characters long."
ERROR_PASSWORDS_DONT_MATCH = "Passwords do not match. Please try again."
ERROR_INVALID_TOKEN = (
    "This password reset link is invalid or has expired. Please request a new one."
)
ERROR_RESET_FAILED = "Sorry, something went wrong while resetting your password. Please try again."


def validate_password_reset(password: str, password_confirm: str) -> Optional[str]:
    if not password or len(password) < 8:
        return ERROR_PASSWORD_TOO_SHORT

    if password != password_confirm:
        return ERROR_PASSWORDS_DONT_MATCH

    return None
