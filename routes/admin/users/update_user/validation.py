from typing import Optional

from core.helpers.logging import get_logger
from routes.dependencies import db

logger = get_logger("admin.users.update.validation")


def validate_and_prepare_email(email: str, name: str, member: bool, user_id: int) -> Optional[str]:
    from routes.admin.users.create_user import generate_guest_email

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


def update_officer_positions(user_id: int, officer_positions: list[str], current_year: int) -> None:
    db(
        "DELETE FROM officer_positions WHERE angler_id = :id AND year = :year",
        {"id": user_id, "year": current_year},
    )
    if officer_positions:
        for position in officer_positions:
            position_cleaned = position.strip()
            if position_cleaned:
                db(
                    "INSERT INTO officer_positions (angler_id, position, year) VALUES (:id, :position, :year)",
                    {"id": user_id, "position": position_cleaned, "year": current_year},
                )
