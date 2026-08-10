"""Profile update routes."""

import os
from typing import Optional

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

from core.db_schema import Angler, get_session
from core.helpers.auth import get_current_user
from core.helpers.logging import get_logger
from routes.auth.profile_update.delete import delete_account
from routes.auth.profile_update.fields import update_profile_fields

router = APIRouter()
logger = get_logger("auth.profile_update")
_is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not _is_test_env)


@router.post("/profile/update")
@limiter.limit("10/minute")
def update_profile(
    request: Request,
    email: str = Form(...),
    phone: str = Form(""),
    year_joined: int = Form(None),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
) -> RedirectResponse:
    """Update user profile including optional password change.

    Rate-limited at 10/minute. The password-change path inside this route
    verifies current_password via bcrypt; without a limit an attacker who
    has hijacked a session could grind bcrypt against current_password to
    elevate the hijack into a permanent account takeover.

    Email-notification preferences are handled separately by
    ``/profile/notifications`` (instant save on toggle), not here.
    """
    return update_profile_fields(
        request, email, phone, year_joined, current_password, new_password, confirm_password
    )


@router.post("/profile/notifications")
@limiter.limit("60/minute")
def update_notifications(
    request: Request,
    email_opt_in: Optional[str] = Form(None),
    notify_news: Optional[str] = Form(None),
    notify_replies: Optional[str] = Form(None),
) -> Response:
    """Persist the notification switches immediately when toggled (HTMX).

    Each switch is an HTML checkbox: a checked box submits a value, an
    unchecked one submits nothing (``None``), which we store as off. Returns a
    small "Saved" indicator swapped into the profile's status slot.
    """
    user = get_current_user(request)
    if not user:
        return HTMLResponse('<span class="text-danger small">Not signed in</span>', status_code=401)

    with get_session() as session:
        angler = session.query(Angler).filter(Angler.id == user["id"]).first()
        if angler is not None:
            angler.email_opt_in = email_opt_in is not None
            angler.notify_news = notify_news is not None
            angler.notify_replies = notify_replies is not None

    logger.info("Notification preferences updated", extra={"user_id": user["id"]})
    return HTMLResponse(
        '<span class="text-green small"><i class="ti ti-check me-1" aria-hidden="true"></i>Saved</span>'
    )


@router.post("/profile/delete")
@limiter.limit("3/hour")
def delete_profile(
    request: Request,
    confirm: str = Form(...),
    current_password: str = Form(...),
) -> RedirectResponse:
    """Delete user account with confirmation + password re-auth.

    Rate-limited at 3/hour. Requires current_password so a CSRF bypass or
    an unlocked-machine attacker can't wipe the account by typing "DELETE".
    """
    return delete_account(request, confirm, current_password)
