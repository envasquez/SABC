"""Password validation helpers for secure authentication."""

import re
from typing import Tuple


def validate_password_strength(password: str) -> Tuple[bool, str]:
    """
    Validate password meets security requirements.

    Requirements:
    - Minimum 12 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one number
    - At least one special character
    - Not in common passwords list

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 12:
        return False, "Password must be at least 12 characters long"

    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/'~`]", password):
        return False, "Password must contain at least one special character"

    # Check against common weak passwords
    common_passwords = [
        "password123",
        "admin123456",
        "letmein12345",
        "welcome12345",
        "qwerty123456",
        "password1234",
        "abc123456789",
        "123456789abc",
    ]

    if password.lower() in common_passwords:
        return False, "Password is too common. Please choose a stronger password"

    # Check for sequential characters (like "123" or "abc")
    if re.search(r"(012|123|234|345|456|567|678|789|890)", password):
        return False, "Password contains sequential numbers"

    if re.search(
        r"(abc|bcd|cde|def|efg|fgh|ghi|hij|ijk|jkl|klm|lmn|mno|nop|opq|pqr|qrs|rst|stu|tuv|uvw|vwx|wxy|xyz)",
        password.lower(),
    ):
        return False, "Password contains sequential letters"

    return True, ""


def get_password_requirements_text() -> str:
    """Get human-readable password requirements for display."""
    return """Password must:
• Be at least 12 characters long
• Include uppercase and lowercase letters
• Include at least one number
• Include at least one special character (!@#$%^&* etc.)
• Not be a common password"""
