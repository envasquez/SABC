"""User update save operations."""

from fastapi import Form, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, get_session
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
        with get_session() as session:
            # Get angler to update
            angler = session.query(Angler).filter(Angler.id == user_id).first()
            if not angler:
                return error_redirect("/admin/users", f"User {user_id} not found")

            # Capture before state
            before = (angler.name, angler.email, angler.phone, angler.member, angler.is_admin)

            # Prepare update data
            update_params = prepare_update_data(user_id, name, email, phone, member, is_admin)
            log_update_initiated(user, user_id, update_params, before)

            # Update angler fields
            angler.name = update_params["name"]
            angler.email = update_params["email"]
            angler.phone = update_params["phone"]
            angler.member = update_params["member"]
            angler.is_admin = update_params["is_admin"]

            # Update officer positions in same transaction
            from core.helpers.timezone import now_local

            current_year = now_local().year
            update_officer_positions(session, user_id, officer_positions, current_year)

            # Flush to get updated state but don't commit yet (context manager will commit)
            session.flush()
            session.refresh(angler)
            after = (angler.name, angler.email, angler.phone, angler.member, angler.is_admin)

        if after != before:
            log_update_completed(request, user, user_id, update_params, before, after)
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
        if (
            "UNIQUE constraint failed: anglers.email" in error_msg
            or "unique constraint" in error_msg.lower()
        ):
            with get_session() as session:
                existing = (
                    session.query(Angler)
                    .filter(Angler.email == update_params["email"], Angler.id != user_id)
                    .first()
                )
                error_msg = (
                    f"Email '{update_params['email']}' already belongs to {existing.name}"
                    if existing
                    else f"Email '{update_params['email']}' is already in use"
                )
        return error_redirect("/admin/users", error_msg)
