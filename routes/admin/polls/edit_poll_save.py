from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from routes.admin.polls.poll_option_helpers import update_or_create_poll_option
from routes.dependencies import db

router = APIRouter()
logger = get_logger("admin.polls.edit")


@router.post("/admin/polls/{poll_id}/edit")
async def update_poll(request: Request, poll_id: int) -> RedirectResponse:
    user = require_admin(request)
    try:
        form = await request.form()
        title = form.get("title", "").strip()
        description = form.get("description", "").strip()
        starts_at = form.get("starts_at", "")
        closes_at = form.get("closes_at", "")
        poll_options = form.getlist("poll_options[]")
        option_ids = form.getlist("option_ids[]")
        if not title:
            return RedirectResponse(
                f"/admin/polls/{poll_id}/edit?error=Title is required", status_code=302
            )
        db(
            """UPDATE polls
               SET title = :title,
                   description = :description,
                   starts_at = :starts_at,
                   closes_at = :closes_at
               WHERE id = :poll_id""",
            {
                "title": title,
                "description": description,
                "starts_at": starts_at if starts_at else None,
                "closes_at": closes_at if closes_at else None,
                "poll_id": poll_id,
            },
        )
        for i, option_text in enumerate(poll_options):
            option_text = option_text.strip()
            option_id = option_ids[i] if i < len(option_ids) and option_ids[i] else None
            update_or_create_poll_option(poll_id, option_text, option_id)
        logger.info(
            "Poll updated successfully",
            extra={
                "admin_user_id": user.get("id"),
                "poll_id": poll_id,
                "title": title,
            },
        )

        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll updated successfully", status_code=302
        )
    except Exception as e:
        logger.error(
            "Error updating poll",
            extra={
                "admin_user_id": user.get("id"),
                "poll_id": poll_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?error=Failed to update poll: {str(e)}", status_code=302
        )
