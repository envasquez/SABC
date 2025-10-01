"""Data preparation for user updates."""

from typing import Any, Dict

from routes.admin.users.update_user.validation import validate_and_prepare_email


def prepare_update_data(
    user_id: int, name: str, email: str, phone: str, member: bool, is_admin: bool
) -> Dict[str, Any]:
    """Prepare and validate user update data.

    Args:
        user_id: The ID of the user to update
        name: User's name
        email: User's email
        phone: User's phone number
        member: Whether the user is a member
        is_admin: Whether the user is an admin

    Returns:
        Dictionary of prepared update parameters
    """
    final_email = validate_and_prepare_email(email, name, member, user_id)
    phone_cleaned = phone.strip() if phone else None

    return {
        "id": user_id,
        "name": name.strip(),
        "email": final_email,
        "phone": phone_cleaned,
        "member": member,
        "is_admin": is_admin,
    }
