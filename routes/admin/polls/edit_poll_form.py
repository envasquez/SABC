from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from core.query_service import QueryService
from routes.dependencies import db, get_lakes_list, templates

router = APIRouter()


@router.get("/admin/polls/{poll_id}/edit")
async def edit_poll_form(request: Request, poll_id: int):
    """Display poll editing form with current data."""
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        # Fetch poll data
        poll_data = db(
            """SELECT p.id, p.title, p.closes_at, p.poll_type, p.starts_at, p.description
               FROM polls p
               WHERE p.id = :poll_id""",
            {"poll_id": poll_id},
        )

        if not poll_data:
            return error_redirect("/polls", "Poll not found")

        poll = poll_data[0]
        context = {"request": request, "user": user, "poll": poll}

        # Get poll options with vote counts
        with engine.connect() as conn:
            qs = QueryService(conn)
            context["poll_options"] = qs.get_poll_options_with_votes(poll_id, include_details=True)

        # Handle tournament location polls differently
        if poll[3] == "tournament_location":  # poll_type
            lakes = get_lakes_list()
            context["lakes"] = lakes

            # Get selected lakes for this poll
            selected_lakes = db(
                """SELECT option_data->>'lake_id' as lake_id
                   FROM poll_options
                   WHERE poll_id = :poll_id""",
                {"poll_id": poll_id},
            )

            selected_lake_ids = set()
            for lake_row in selected_lakes:
                if lake_row[0] is not None:
                    selected_lake_ids.add(int(lake_row[0]))

            context["selected_lake_ids"] = selected_lake_ids
            return templates.TemplateResponse("admin/edit_tournament_poll.html", context)
        else:
            return templates.TemplateResponse("admin/edit_poll.html", context)

    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to load poll: {str(e)}", status_code=302)
