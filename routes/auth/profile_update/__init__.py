"""Profile update routes."""

import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from routes.auth.profile_update.delete import delete_account
from routes.auth.profile_update.fields import update_profile_fields

router = APIRouter()
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
    """
    return update_profile_fields(
        request, email, phone, year_joined, current_password, new_password, confirm_password
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
