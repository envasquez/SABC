"""Poll creation form rendering."""

from fastapi import Query, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, get_all_ramps, get_lakes_list, templates


async def create_poll_form(request: Request, event_id: int = Query(None)):
    """Render the poll creation form.

    Args:
        request: The FastAPI request object
        event_id: Optional event ID to associate with the poll

    Returns:
        Template response with the poll creation form
    """
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        events = db(
            "SELECT id, date, name, event_type, description FROM events WHERE date >= CURRENT_DATE AND event_type = 'sabc_tournament' ORDER BY date"
        )
        lakes = get_lakes_list()
        ramps = get_all_ramps()

        selected_event = None
        if event_id is not None:
            event_data = db(
                "SELECT id, date, name, event_type, description FROM events WHERE id = :event_id",
                {"event_id": event_id},
            )
            if not event_data:
                return error_redirect("/admin/events", "Event not found")
            selected_event = event_data[0]

            existing_poll = db(
                "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
            )
            if existing_poll:
                return RedirectResponse(
                    f"/admin/polls/{existing_poll[0][0]}/edit?info=Poll already exists for this event",
                    status_code=302,
                )

        context = {
            "request": request,
            "user": user,
            "events": events,
            "selected_event": selected_event,
            "lakes": lakes,
            "ramps": ramps,
        }
        return templates.TemplateResponse("admin/create_poll.html", context)
    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to load poll creation form: {str(e)}", status_code=302
        )
