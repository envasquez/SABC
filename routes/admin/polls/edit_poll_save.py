from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Poll, get_session
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_string
from core.helpers.logging import get_logger
from routes.admin.polls.poll_option_helpers import update_or_create_poll_option

router = APIRouter()
logger = get_logger("admin.polls.edit")


@router.post("/admin/polls/{poll_id}/edit")
async def update_poll(request: Request, poll_id: int) -> RedirectResponse:
    user = require_admin(request)
    try:
        form_data = await request.form()
        title = get_form_string(form_data, "title")
        description = get_form_string(form_data, "description")
        starts_at_str = get_form_string(form_data, "starts_at")
        closes_at_str = get_form_string(form_data, "closes_at")
        poll_options = form_data.getlist("poll_options[]")
        option_ids = form_data.getlist("option_ids[]")

        if not title:
            return RedirectResponse(
                f"/admin/polls/{poll_id}/edit?error=Title is required", status_code=302
            )

        # Parse datetime strings
        starts_at: Optional[datetime] = None
        closes_at: Optional[datetime] = None
        if starts_at_str:
            starts_at = datetime.fromisoformat(starts_at_str)
        if closes_at_str:
            closes_at = datetime.fromisoformat(closes_at_str)

        with get_session() as session:
            poll = session.query(Poll).filter(Poll.id == poll_id).first()
            if poll:
                poll.title = title
                poll.description = description
                poll.starts_at = starts_at
                poll.closes_at = closes_at

        # Update poll options
        for i, option_text in enumerate(poll_options):
            # Ensure we have a string value
            text = option_text if isinstance(option_text, str) else ""
            text = text.strip()
            option_id_val = option_ids[i] if i < len(option_ids) and option_ids[i] else None
            option_id_str = option_id_val if isinstance(option_id_val, str) else None
            update_or_create_poll_option(poll_id, text, option_id_str)

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
