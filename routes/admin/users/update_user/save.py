"""User update save operations."""

from datetime import datetime

from fastapi import Form, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.admin.users.update_user.logging import (
    log_update_completed,
    log_update_exception,
    log_update_failed,
    log_update_initiated,
)
from routes.admin.users.update_user.prepare import prepare_update_data
from routes.admin.users.update_user.validation import update_officer_positions
from routes.dependencies import db


async def update_user(
    request: Request,
    user_id: int,
    name: str = Form(...),
    email: str = Form(""),
    phone: str = Form(""),
    member: bool = Form(False),
    is_admin: bool = Form(False),
    officer_positions: list[str] = Form([]),
) -> RedirectResponse:
    """Handle user update form submission."""
    user = require_admin(request)
    try:
        before = db(
            "SELECT name, email, phone, member, is_admin FROM anglers WHERE id = :id",
            {"id": user_id},
        )
        if not before:
            return error_redirect("/admin/users", f"User {user_id} not found")

        update_params = prepare_update_data(user_id, name, email, phone, member, is_admin)
        log_update_initiated(user, user_id, update_params, before[0])

        query = "UPDATE anglers SET name = :name, email = :email, phone = :phone, member = :member, is_admin = :is_admin WHERE id = :id"
        db(query, update_params)

        current_year = datetime.now().year
        update_officer_positions(user_id, officer_positions, current_year)

        after = db(
            "SELECT name, email, phone, member, is_admin FROM anglers WHERE id = :id",
            {"id": user_id},
        )

        if after and after[0] != before[0]:
            log_update_completed(request, user, user_id, update_params, before[0], after[0])
            return RedirectResponse(
                "/admin/users?success=User updated and verified", status_code=302
            )
        else:
            log_update_failed(user, user_id, update_params)
            return RedirectResponse(
                "/admin/users?error=Update failed - no changes saved", status_code=302
            )

    except Exception as e:
        log_update_exception(user, user_id, e, update_params if "update_params" in locals() else {})
        error_msg = str(e)
        if "UNIQUE constraint failed: anglers.email" in error_msg:
            existing = db(
                "SELECT name FROM anglers WHERE email = :email AND id != :id",
                {"email": update_params["email"], "id": user_id},
            )
            error_msg = (
                f"Email '{update_params['email']}' already belongs to {existing[0][0]}"
                if existing
                else f"Email '{update_params['email']}' is already in use"
            )
        return error_redirect("/admin/users", error_msg)
