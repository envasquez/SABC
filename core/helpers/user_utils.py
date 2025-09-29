"""User utility functions for common operations."""

from typing import Optional

from core.database import db


def generate_guest_email(name: str, existing_user_id: Optional[int] = None) -> Optional[str]:
    """
    Generate unique email for guest user based on name.

    Args:
        name: User's full name
        existing_user_id: If updating existing user, exclude this ID from uniqueness check

    Returns:
        Unique email address or None if name is invalid
    """
    name_parts = name.lower().split()
    if len(name_parts) < 2:
        return None

    # Clean name parts (alphanumeric only)
    first_clean = "".join(c for c in name_parts[0] if c.isalnum())
    last_clean = "".join(c for c in name_parts[-1] if c.isalnum())

    if not first_clean or not last_clean:
        return None

    # Try base email first
    proposed_email = f"{first_clean}.{last_clean}@sabc.com"

    # Build query to check if email exists
    query = "SELECT id FROM anglers WHERE email = :email"
    params = {"email": proposed_email}

    if existing_user_id:
        query += " AND id != :user_id"
        params["user_id"] = existing_user_id

    # Check if base email is available
    if not db(query, params):
        return proposed_email

    # Try numbered versions
    for counter in range(2, 100):
        numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
        params["email"] = numbered_email

        if not db(query, params):
            return numbered_email

    # Couldn't find unique email after 100 attempts
    return None
