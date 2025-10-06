from fastapi import Query, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Event, Poll, get_session
from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import get_all_ramps, get_lakes_list, templates


async def create_poll_form(request: Request, event_id: int = Query(None)):
    user = require_admin(request)
    try:
        with get_session() as session:
            # Get upcoming SABC tournaments
            events = (
                session.query(Event)
                .filter(Event.date >= "CURRENT_DATE", Event.event_type == "sabc_tournament")
                .order_by(Event.date)
                .all()
            )

            # Convert to tuple format for template compatibility
            events_list = [(e.id, e.date, e.name, e.event_type, e.description) for e in events]

            lakes = get_lakes_list()
            ramps = get_all_ramps()

            selected_event = None
            if event_id is not None:
                event = session.query(Event).filter(Event.id == event_id).first()
                if not event:
                    return error_redirect("/admin/events", "Event not found")

                selected_event = (
                    event.id,
                    event.date,
                    event.name,
                    event.event_type,
                    event.description,
                )

                # Check if poll already exists for this event
                existing_poll = session.query(Poll).filter(Poll.event_id == event_id).first()
                if existing_poll:
                    return RedirectResponse(
                        f"/admin/polls/{existing_poll.id}/edit?info=Poll already exists for this event",
                        status_code=302,
                    )

        context = {
            "request": request,
            "user": user,
            "events": events_list,
            "selected_event": selected_event,
            "lakes": lakes,
            "ramps": ramps,
        }
        return templates.TemplateResponse("admin/create_poll.html", context)
    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to load poll creation form: {str(e)}", status_code=302
        )
