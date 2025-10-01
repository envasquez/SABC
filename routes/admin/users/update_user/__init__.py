"""User update module."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from routes.admin.users.update_user.save import update_user
from routes.admin.users.update_user.validation import (
    update_officer_positions,
    validate_and_prepare_email,
)

router = APIRouter()


@router.post("/admin/users/{user_id}/edit")
async def post_update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    member: bool = Form(False),
    is_admin: bool = Form(False),
    officer_positions: list[str] = Form([]),
) -> RedirectResponse:
    """POST route for user update."""
    return await update_user(
        request, user_id, name, email, phone, member, is_admin, officer_positions
    )


__all__ = ["router", "update_user", "validate_and_prepare_email", "update_officer_positions"]
