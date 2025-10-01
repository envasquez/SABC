from typing import Any, Dict

from routes.admin.users.update_user.validation import validate_and_prepare_email


def prepare_update_data(
    user_id: int, name: str, email: str, phone: str, member: bool, is_admin: bool
) -> Dict[str, Any]:
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
