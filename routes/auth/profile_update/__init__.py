"""Profile update routes."""

from fastapi import APIRouter, Form, Request

from routes.auth.profile_update.delete import delete_account
from routes.auth.profile_update.fields import update_profile_fields

router = APIRouter()


@router.post("/profile/update")
async def update_profile(
    request: Request,
    email: str = Form(...),
    phone: str = Form(""),
    year_joined: int = Form(None),
    current_password: str = Form(""),
    new_password: str = Form(""),
    confirm_password: str = Form(""),
):
    """Update user profile including optional password change."""
    return await update_profile_fields(
        request, email, phone, year_joined, current_password, new_password, confirm_password
    )


@router.post("/profile/delete")
async def delete_profile(request: Request, confirm: str = Form(...)):
    """Delete user account with confirmation."""
    return await delete_account(request, confirm)
