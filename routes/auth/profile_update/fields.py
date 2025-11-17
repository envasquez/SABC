"""Field update logic for profile updates."""

from fastapi import Request
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, get_session
from core.helpers.logging import get_logger
from routes.auth.profile_update.password import handle_password_change
from routes.auth.validation import validate_phone_number
from routes.dependencies import get_current_user

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
    if not (user := get_current_user(request)):
        return RedirectResponse("/login")

    try:
        email = email.lower().strip()

        is_valid, formatted_phone, error_msg = validate_phone_number(phone)
        if not is_valid:
            return RedirectResponse(f"/profile?error={error_msg}", status_code=303)
        phone = formatted_phone  # type: ignore[assignment]

        # Handle password change before database update
        password_changed = False
        if current_password or new_password or confirm_password:
            ip_address = request.client.host if request.client else "unknown"
            success, error = handle_password_change(
                user, current_password, new_password, confirm_password, ip_address
            )
            if not success:
                return RedirectResponse(f"/profile?error={error}", status_code=303)
            password_changed = True

        # Use single session for both email check and update to prevent race condition
        with get_session() as session:
            # Check email uniqueness and update in same transaction
            existing_email = (
                session.query(Angler).filter(Angler.email == email, Angler.id != user["id"]).first()
            )
            if existing_email:
                return RedirectResponse(
                    "/profile?error=Email is already in use by another user", status_code=303
                )

            # Update user profile in same transaction
            angler = session.query(Angler).filter(Angler.id == user["id"]).first()
            if angler:
                angler.email = email
                angler.phone = phone
                angler.year_joined = year_joined

        updated_fields = {"email": email, "phone": phone, "year_joined": year_joined}
        if password_changed:
            updated_fields["password"] = "changed"  # nosec B105 - Not a password, just a flag

        logger.info(
            "User profile updated", extra={"user_id": user["id"], "updated_fields": updated_fields}
        )

        success_msg = "Profile updated successfully"
        if password_changed:
            success_msg += " and password changed"
        return RedirectResponse(f"/profile?success={success_msg}", status_code=303)

    except Exception as e:
        logger.error(
            "Profile update error", extra={"user_id": user["id"], "error": str(e)}, exc_info=True
        )
        return RedirectResponse("/profile?error=Failed to update profile", status_code=303)
