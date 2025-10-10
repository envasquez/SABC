import json

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Poll, PollOption, engine, get_session
from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect
from core.query_service import QueryService
from routes.dependencies import get_lakes_list, templates

logger = get_logger(__name__)

router = APIRouter()


@router.get("/admin/polls/{poll_id}/edit")
async def edit_poll_form(request: Request, poll_id: int):
    """Display poll editing form with current data."""
    user = require_admin(request)
    try:
        with get_session() as session:
            # Fetch poll data
            poll_obj = session.query(Poll).filter(Poll.id == poll_id).first()

            if not poll_obj:
                return error_redirect("/polls", "Poll not found")

            # Convert to tuple format for template compatibility
            poll = (
                poll_obj.id,
                poll_obj.title,
                poll_obj.closes_at,
                poll_obj.poll_type,
                poll_obj.starts_at,
                poll_obj.description,
            )

            context = {"request": request, "user": user, "poll": poll}

            # Get poll options with vote counts
            with engine.connect() as conn:
                qs = QueryService(conn)
                context["poll_options"] = qs.get_poll_options_with_votes(  # type: ignore[assignment]
                    poll_id, include_details=True
                )

            # Handle tournament location polls differently
            if poll_obj.poll_type == "tournament_location":
                lakes = get_lakes_list()
                context["lakes"] = lakes  # type: ignore[assignment]

                # Get selected lakes for this poll
                poll_options = session.query(PollOption).filter(PollOption.poll_id == poll_id).all()

                selected_lake_ids = set()
                for option in poll_options:
                    if option.option_data:
                        try:
                            data = json.loads(option.option_data)
                            if "lake_id" in data and data["lake_id"] is not None:
                                selected_lake_ids.add(int(data["lake_id"]))
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(
                                f"Invalid JSON in poll option {option.id} for poll {poll_id}: {e}. "
                                f"Skipping this option."
                            )
                            # Skip this option, continue with others

                context["selected_lake_ids"] = selected_lake_ids
                return templates.TemplateResponse("admin/edit_tournament_poll.html", context)
            else:
                return templates.TemplateResponse("admin/edit_poll.html", context)

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to load poll: {str(e)}", status_code=302)
