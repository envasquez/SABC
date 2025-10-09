from datetime import timedelta
from typing import Optional, Tuple

from core.db_schema import Event, Poll, get_session
from core.helpers.response import error_redirect
from core.helpers.timezone import now_local


def validate_and_get_event(
    poll_type: str, event_id: Optional[int]
) -> Tuple[Optional[tuple], Optional[object]]:
    if poll_type == "tournament_location" and event_id:
        with get_session() as session:
            event_obj = session.query(Event).filter(Event.id == event_id).first()

            if not event_obj:
                return None, error_redirect("/admin/events", "Event not found")

            # Convert to tuple format for compatibility
            event = (
                event_obj.id,
                event_obj.name,
                event_obj.event_type,
                event_obj.date.strftime("%Y-%m-%d"),
            )

            # Check if poll already exists
            existing_poll = session.query(Poll).filter(Poll.event_id == event_id).first()

            if existing_poll:
                from fastapi.responses import RedirectResponse

                return None, RedirectResponse(
                    f"/admin/polls/{existing_poll.id}/edit?error=Poll already exists for this event",
                    status_code=302,
                )

            return event, None
    return None, None


def generate_poll_title(poll_type: str, title: str, event: Optional[tuple]) -> str:
    if not title and poll_type == "tournament_location" and event:
        return f"{event[1]} Lake Selection Poll"
    elif not title and event:
        return f"Poll for {event[1]}"
    elif not title:
        return "Generic Poll"
    return title


def generate_starts_at(starts_at: str, event: Optional[tuple]) -> str:
    if not starts_at:
        if event:
            # Still need datetime.strptime for parsing the event date string
            from datetime import datetime

            event_date = datetime.strptime(event[3], "%Y-%m-%d")
            return (event_date - timedelta(days=7)).isoformat()
        else:
            return (now_local() + timedelta(days=1)).isoformat()
    return starts_at


def generate_description(description: str, event: Optional[tuple]) -> str:
    if description:
        return description
    if event:
        return f"Vote for location for {event[1]}"
    return "Vote for your preferred option"
