"""Phone number formatting utilities."""

from typing import Optional


def format_phone_number(phone: Optional[str]) -> Optional[str]:
    """
    Format a phone number to (XXX) XXX-XXXX format.

    Args:
        phone: Raw phone number string

    Returns:
        Formatted phone number or None if invalid/empty
    """
    if not phone:
        return None

    # Remove all non-numeric characters
    phone_digits = "".join(filter(str.isdigit, phone.strip()))

    if not phone_digits:
        return None

    # Handle 11-digit numbers starting with 1
    if len(phone_digits) == 11 and phone_digits[0] == "1":
        phone_digits = phone_digits[1:]

    # Format if we have exactly 10 digits
    if len(phone_digits) == 10:
        return f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"

    # Return None for invalid lengths
    return None


def validate_phone_number(phone: Optional[str]) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Validate and format a phone number.

    Args:
        phone: Raw phone number string

    Returns:
        Tuple of (is_valid, formatted_phone, error_message)
    """
    if not phone:
        return True, None, None

    # Remove all non-numeric characters
    phone_digits = "".join(filter(str.isdigit, phone.strip()))

    if not phone_digits:
        return True, None, None  # Empty is valid (optional field)

    # Handle 11-digit numbers starting with 1
    if len(phone_digits) == 11 and phone_digits[0] == "1":
        phone_digits = phone_digits[1:]

    # Check if we have exactly 10 digits
    if len(phone_digits) == 10:
        formatted = f"({phone_digits[:3]}) {phone_digits[3:6]}-{phone_digits[6:]}"
        return True, formatted, None
    elif len(phone_digits) < 10:
        return False, None, "Phone number must have 10 digits"
    else:
        return False, None, "Phone number has too many digits"
