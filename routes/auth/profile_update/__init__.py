"""Profile update routes."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from routes.auth.profile_update.delete import delete_account
from routes.auth.profile_update.fields import update_profile_fields

router = APIRouter()


@router.post("/profile/update")
def update_profile(
    request: Request,
    email: str = Form(...),
    phone: str = Form(""),
    year_joined: int = Form(None),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
) -> RedirectResponse:
    """Update user profile including optional password change."""
    return update_profile_fields(
        request, email, phone, year_joined, current_password, new_password, confirm_password
    )


@router.post("/profile/delete")
def delete_profile(request: Request, confirm: str = Form(...)) -> RedirectResponse:
    """Delete user account with confirmation."""
    return delete_account(request, confirm)
