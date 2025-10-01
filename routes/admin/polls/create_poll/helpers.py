from datetime import datetime, timedelta
from typing import Optional, Tuple

from core.helpers.response import error_redirect
from routes.dependencies import db


def validate_and_get_event(
    poll_type: str, event_id: Optional[int]
) -> Tuple[Optional[tuple], Optional[object]]:
    if poll_type == "tournament_location" and event_id:
        event_data = db(
            "SELECT id, name, event_type, date FROM events WHERE id = :event_id",
            {"event_id": event_id},
        )
        if not event_data:
            return None, error_redirect("/admin/events", "Event not found")
        event = event_data[0]
        existing_poll = db(
            "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
        )
        if existing_poll:
            from fastapi.responses import RedirectResponse

            return None, RedirectResponse(
                f"/admin/polls/{existing_poll[0][0]}/edit?error=Poll already exists for this event",
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
            event_date = datetime.strptime(event[3], "%Y-%m-%d")
            return (event_date - timedelta(days=7)).isoformat()
        else:
            return (datetime.now() + timedelta(days=1)).isoformat()
    return starts_at


def generate_description(description: str, event: Optional[tuple]) -> str:
    if description:
        return description
    if event:
        return f"Vote for location for {event[1]}"
    return "Vote for your preferred option"
