from fastapi import APIRouter, Request

from core.db_schema import Angler, OfficerPosition, get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import templates

router = APIRouter()


@router.get("/admin/users/{user_id}/edit")
async def edit_user_page(request: Request, user_id: int):
    user = require_admin(request)

    with get_session() as session:
        # Get the angler to edit
        edit_angler = session.query(Angler).filter(Angler.id == user_id).first()
        if not edit_angler:
            return error_redirect("/admin/users", "User not found")

        # Extract data while in session
        edit_user = {
            "id": edit_angler.id,
            "name": edit_angler.name,
            "email": edit_angler.email,
            "phone": edit_angler.phone,
            "member": edit_angler.member,
            "is_admin": edit_angler.is_admin,
            "dues_paid_through": edit_angler.dues_paid_through,
        }

        # Get officer positions for current year
        from core.helpers.timezone import now_local

        current_year = now_local().year
        positions = (
            session.query(OfficerPosition.position)
            .filter(
                OfficerPosition.angler_id == user_id,
                OfficerPosition.year == current_year,
            )
            .order_by(OfficerPosition.position)
            .all()
        )
        current_officer_positions = [pos.position for pos in positions]

    return templates.TemplateResponse(
        "admin/edit_user.html",
        {
            "request": request,
            "user": user,
            "edit_user": edit_user,
            "current_officer_positions": current_officer_positions,
            "current_year": current_year,
        },
    )
