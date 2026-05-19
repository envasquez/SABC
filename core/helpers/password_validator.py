"""Password validation helpers for secure authentication."""

import re
from typing import Tuple

# Well-known weak passwords. The complexity rules require upper+lower+digit+
# special, so this list focuses on realistic weak passwords that still satisfy
# those rules, plus generic entries. All entries are lowercase.
COMMON_PASSWORDS = [
    # Existing entries
    "password123",
    "admin123456",
    "letmein12345",
    "welcome12345",
    "qwerty123456",
    "password1234",
    "abc123456789",
    "123456789abc",
    # Realistic weak passwords with complexity characters
    "password123!",
    "password1234!",
    "passw0rd123!",
    "p@ssword1234",
    "p@ssw0rd1234",
    "admin@1234567",
    "admin123456!",
    "qwerty123!@#",
    "qwerty12345!",
    "welcome@123456",
    "welcome123!@#",
    "letmein123!@#",
    "letmein@123456",
    "iloveyou123!",
    "monkey123!@#",
    "dragon123!@#",
    "sunshine123!",
    "football123!",
    "baseball123!",
    "superman123!",
    "trustno1@123",
    "master123!@#",
    "shadow123!@#",
    "michael123!@#",
    "abc123456789!",
    "changeme123!",
    "default123!@#",
    "secret123!@#",
    "test1234567!",
]


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
        return False, "Password must contain at least one digit"

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/'~`]", password):
        return False, "Password must contain at least one special character"

    # Check against common weak passwords
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common. Please choose a stronger password"

    # Check for sequential numbers (like "123")
    if re.search(r"(012|123|234|345|456|567|678|789|890)", password):
        return False, "Password contains sequential numbers"

    return True, ""


def get_password_requirements_text() -> str:
    """Get human-readable password requirements for display."""
    return """Password must:
• Be at least 12 characters long
• Include uppercase and lowercase letters
• Include at least one number
• Include at least one special character (!@#$%^&* etc.)
• Not be a common password"""
