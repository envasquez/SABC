"""Email generation helpers for user management."""

from routes.dependencies import db


def generate_guest_email(name: str, user_id: int | None = None) -> str | None:
    """Generate a unique guest email for a user based on their name."""
    name_parts = name.lower().split()
    if len(name_parts) < 2:
        return None

    first_clean = "".join(c for c in name_parts[0] if c.isalnum())
    last_clean = "".join(c for c in name_parts[-1] if c.isalnum())
    proposed_email = f"{first_clean}.{last_clean}@sabc.com"

    check_query = "SELECT id FROM anglers WHERE email = :email"
    params = {"email": proposed_email}
    if user_id is not None:
        check_query += " AND id != :id"
        params["id"] = user_id

    if not db(check_query, params):
        return proposed_email

    for counter in range(2, 100):
        numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
        params["email"] = numbered_email
        if not db(check_query, params):
            return numbered_email

    return None
