from fastapi import Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from routes.admin.polls.create_poll.helpers import (
    generate_description,
    generate_poll_title,
    generate_starts_at,
    validate_and_get_event,
)
from routes.admin.polls.create_poll.options import (
    create_generic_poll_options,
    create_other_poll_options,
    create_tournament_location_options,
)
from routes.dependencies import db


logger = get_logger("admin.polls.create")


async def create_poll(request: Request) -> RedirectResponse:
    user = require_admin(request)
    try:
        form = await request.form()
        event_id_raw = form.get("event_id")
        event_id = int(event_id_raw) if event_id_raw and isinstance(event_id_raw, str) else None
        poll_type = form.get("poll_type", "")
        title = form.get("title", "")
        description = form.get("description", "")
        closes_at = form.get("closes_at", "")
        starts_at = form.get("starts_at", "")

        event, error_response = validate_and_get_event(poll_type, event_id)
        if error_response:
            return error_response

        title = generate_poll_title(poll_type, title, event)
        starts_at = generate_starts_at(starts_at, event)
        description = generate_description(description, event)

        poll_result = db(
            "INSERT INTO polls (title, description, poll_type, event_id, created_by, starts_at, closes_at) VALUES (:title, :description, :poll_type, :event_id, :created_by, :starts_at, :closes_at) RETURNING id",
            {
                "title": title,
                "description": description,
                "poll_type": poll_type,
                "event_id": event_id if event_id else None,
                "created_by": user["id"],
                "starts_at": starts_at,
                "closes_at": closes_at,
            },
        )
        poll_id = poll_result[0][0]
        if poll_type == "tournament_location":
            create_tournament_location_options(poll_id, form, event)
        elif poll_type == "generic":
            create_generic_poll_options(poll_id, form)
        else:
            create_other_poll_options(poll_id, form)
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll created successfully", status_code=302
        )
    except Exception as e:
        logger.error(
            "Error creating poll",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id if "event_id" in locals() else None,
                "poll_type": poll_type if "poll_type" in locals() else None,
                "error": str(e),
            },
            exc_info=True,
        )
        return RedirectResponse(
            f"/admin/events?error=Failed to create poll: {str(e)}", status_code=302
        )
