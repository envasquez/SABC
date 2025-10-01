from datetime import datetime

from fastapi import APIRouter, Request

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/admin/users/{user_id}/edit")
async def edit_user_page(request: Request, user_id: int):
    user = require_admin(request)
    edit_user = db(
        "SELECT id, name, email, phone, member, is_admin FROM anglers WHERE id = :id",
        {"id": user_id},
    )
    if not edit_user:
        return error_redirect("/admin/users", "User not found")

    current_year = datetime.now().year
    officer_positions_result = db(
        "SELECT position FROM officer_positions WHERE angler_id = :id AND year = :year ORDER BY position",
        {"id": user_id, "year": current_year},
    )
    current_officer_positions = (
        [row[0] for row in officer_positions_result] if officer_positions_result else []
    )

    return templates.TemplateResponse(
        "admin/edit_user.html",
        {
            "request": request,
            "user": user,
            "edit_user": edit_user[0],
            "current_officer_positions": current_officer_positions,
            "current_year": current_year,
        },
    )
