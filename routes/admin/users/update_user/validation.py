from typing import Optional

from core.db_schema import OfficerPosition
from core.helpers.logging import get_logger

logger = get_logger("admin.users.update.validation")


def validate_and_prepare_email(email: str, name: str, member: bool, user_id: int) -> Optional[str]:
    from routes.admin.users.email_helpers import generate_guest_email

    email_cleaned = email.strip() if email else ""
    final_email = None
    if email_cleaned:
        final_email = email_cleaned.lower()
    elif not member:
        final_email = generate_guest_email(name.strip(), user_id)
        if final_email:
            logger.info(
                "Auto-generated email for guest user",
                extra={
                    "user_id": user_id,
                    "user_name": name,
                    "generated_email": final_email,
                },
            )

    return final_email


def update_officer_positions(
    session, user_id: int, officer_positions: list[str], current_year: int
) -> None:
    """Update officer positions for a user within an existing session transaction.

    Args:
        session: Active SQLAlchemy session (must be managed by caller)
        user_id: User ID to update positions for
        officer_positions: List of position titles
        current_year: Year for the positions
    """
    # Delete existing officer positions for this user and year
    session.query(OfficerPosition).filter(
        OfficerPosition.angler_id == user_id,
        OfficerPosition.year == current_year,
    ).delete()

    # Add new officer positions
    if officer_positions:
        for position in officer_positions:
            position_cleaned = position.strip()
            if position_cleaned:
                officer_position = OfficerPosition(
                    angler_id=user_id,
                    position=position_cleaned,
                    year=current_year,
                )
                session.add(officer_position)
