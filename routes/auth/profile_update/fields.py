"""Field update logic for profile updates."""

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.helpers.logging import get_logger
from routes.auth.profile_update.password import handle_password_change
from routes.auth.validation import validate_phone_number
from routes.dependencies import db, u

logger = get_logger("auth.profile_update.fields")


async def update_profile_fields(
    request: Request,
    email: str,
    phone: str,
    year_joined: int,
    current_password: str,
    new_password: str,
    confirm_password: str,
) -> RedirectResponse:
    """Handle profile field updates including optional password change."""
    if not (user := u(request)):
        return RedirectResponse("/login")

    try:
        email = email.lower().strip()

        is_valid, formatted_phone, error_msg = validate_phone_number(phone)
        if not is_valid:
            return RedirectResponse(f"/profile?error={error_msg}", status_code=302)
        phone = formatted_phone

        existing_email = db(
            "SELECT id FROM anglers WHERE email = :email AND id != :user_id",
            {"email": email, "user_id": user["id"]},
        )
        if existing_email:
            return RedirectResponse(
                "/profile?error=Email is already in use by another user", status_code=302
            )

        password_changed = False
        if current_password or new_password or confirm_password:
            ip_address = request.client.host if request.client else "unknown"
            success, error = handle_password_change(
                user, current_password, new_password, confirm_password, ip_address
            )
            if not success:
                return RedirectResponse(f"/profile?error={error}", status_code=302)
            password_changed = True

        db(
            """
            UPDATE anglers SET email = :email, phone = :phone, year_joined = :year_joined
            WHERE id = :user_id
        """,
            {"email": email, "phone": phone, "year_joined": year_joined, "user_id": user["id"]},
        )

        updated_fields = {"email": email, "phone": phone, "year_joined": year_joined}
        if password_changed:
            updated_fields["password"] = "changed"

        logger.info(
            "User profile updated", extra={"user_id": user["id"], "updated_fields": updated_fields}
        )

        success_msg = "Profile updated successfully"
        if password_changed:
            success_msg += " and password changed"
        return RedirectResponse(f"/profile?success={success_msg}", status_code=302)

    except Exception as e:
        logger.error(
            "Profile update error", extra={"user_id": user["id"], "error": str(e)}, exc_info=True
        )
        return RedirectResponse("/profile?error=Failed to update profile", status_code=302)
