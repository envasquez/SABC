import json
from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Poll, PollOption, PollVote, get_session
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
    kept_options_with_votes = []  # Track options we couldn't remove (for user feedback)
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
                # Smart update strategy to handle polls with existing votes
                # 1. Get existing options with their lake_ids
                existing_options = (
                    session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
                )
                existing_lake_ids = set()
                option_map: Dict[int, PollOption] = {}  # lake_id -> option

                for option in existing_options:
                    if option.option_data:
                        try:
                            data = json.loads(option.option_data)
                            if "lake_id" in data:
                                lake_id = data["lake_id"]
                                existing_lake_ids.add(lake_id)
                                option_map[lake_id] = option
                        except json.JSONDecodeError:
                            pass

                # 2. Determine which lakes to keep, add, remove
                selected_lake_ids = (
                    set(int(lid) for lid in lake_ids if isinstance(lid, str)) if lake_ids else set()
                )

                # If no lakes selected, use all lakes as default
                if not selected_lake_ids:
                    all_lakes = get_lakes_list()
                    selected_lake_ids = set(lake["id"] for lake in all_lakes)

                lakes_to_add = selected_lake_ids - existing_lake_ids
                lakes_to_remove = existing_lake_ids - selected_lake_ids

                # 3. Add new options for newly selected lakes
                for lake_id in lakes_to_add:
                    lake_name = find_lake_by_id(lake_id, "name")
                    if lake_name:
                        new_option = PollOption(
                            poll_id=poll_id,
                            option_text=lake_name,
                            option_data=json.dumps({"lake_id": lake_id}),
                        )
                        session.add(new_option)

                # 4. Remove options that are no longer selected (only if they have no votes)
                for lake_id in lakes_to_remove:
                    opt_to_remove: Optional[PollOption] = option_map.get(lake_id)
                    if opt_to_remove:
                        # Check if this option has any votes
                        vote_count = (
                            session.query(PollVote)
                            .filter(PollVote.option_id == opt_to_remove.id)
                            .count()
                        )

                        if vote_count == 0:
                            # Safe to delete - no votes
                            session.delete(opt_to_remove)
                        else:
                            # Option has votes - keep it but log a warning
                            kept_options_with_votes.append(opt_to_remove.option_text)
                            logger.warning(
                                f"Cannot remove poll option (ID {opt_to_remove.id}) - has {vote_count} vote(s)",
                                extra={
                                    "poll_id": poll_id,
                                    "option_id": opt_to_remove.id,
                                    "lake_id": lake_id,
                                    "vote_count": vote_count,
                                },
                            )
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

        # Build success message
        success_msg = "Poll updated successfully"
        if kept_options_with_votes:
            success_msg += f". Note: Some options ({', '.join(kept_options_with_votes)}) could not be removed because they have existing votes."

        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success={success_msg}", status_code=302
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
