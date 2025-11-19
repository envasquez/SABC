import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Poll, PollOption, get_session
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_string
from core.helpers.logging import get_logger
from routes.admin.polls.poll_option_helpers import update_or_create_poll_option
from routes.dependencies import find_lake_by_id, get_lakes_list

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
        lake_ids = form_data.getlist("lake_ids")  # For tournament location polls

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
            if not poll:
                return RedirectResponse("/admin/polls?error=Poll not found", status_code=302)

            poll.title = title
            poll.description = description
            poll.starts_at = starts_at  # type: ignore[assignment]
            poll.closes_at = closes_at  # type: ignore[assignment]

            # Handle tournament location polls differently
            if poll.poll_type == "tournament_location":
                # Delete existing options
                session.query(PollOption).filter(PollOption.poll_id == poll_id).delete()

                # Create new options based on selected lakes
                if lake_ids:
                    for lake_id_raw in lake_ids:
                        lake_id = int(lake_id_raw)
                        lake_name = find_lake_by_id(lake_id, "name")
                        if lake_name:
                            new_option = PollOption(
                                poll_id=poll_id,
                                option_text=lake_name,
                                option_data=json.dumps({"lake_id": lake_id}),
                            )
                            session.add(new_option)
                else:
                    # If no lakes selected, use all lakes as default
                    all_lakes = get_lakes_list()
                    for lake in all_lakes:
                        new_option = PollOption(
                            poll_id=poll_id,
                            option_text=lake["display_name"],
                            option_data=json.dumps({"lake_id": lake["id"]}),
                        )
                        session.add(new_option)
            else:
                # Handle simple/generic polls - update options in place
                # Note: This code runs outside the session context, should be moved inside
                pass

        # For non-tournament polls, update options outside session context
        # This maintains backward compatibility with existing behavior
        if not poll or poll.poll_type != "tournament_location":
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
