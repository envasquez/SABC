from core.db_schema import Angler, get_session


def generate_guest_email(name: str, user_id: int | None = None) -> str | None:
    name_parts = name.lower().split()
    if len(name_parts) < 2:
        return None
    first_clean = "".join(c for c in name_parts[0] if c.isalnum())
    last_clean = "".join(c for c in name_parts[-1] if c.isalnum())
    proposed_email = f"{first_clean}.{last_clean}@sabc.com"

    with get_session() as session:
        # Check if proposed email exists
        query = session.query(Angler.id).filter(Angler.email == proposed_email)
        if user_id is not None:
            query = query.filter(Angler.id != user_id)

        if not query.first():
            return proposed_email

        # Try numbered variants
        for counter in range(2, 100):
            numbered_email = f"{first_clean}.{last_clean}{counter}@sabc.com"
            query = session.query(Angler.id).filter(Angler.email == numbered_email)
            if user_id is not None:
                query = query.filter(Angler.id != user_id)

            if not query.first():
                return numbered_email

    return None
