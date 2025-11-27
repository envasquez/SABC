"""Calendar data fetching and processing."""

import calendar as cal
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from sqlalchemy import extract

from core.db_schema import Event, Poll, Tournament, get_session
from routes.pages.calendar_structure import build_calendar_structure


def get_year_calendar_data(year: int) -> Tuple[List[Any], Dict[str, Any], Set[str]]:
    """Get calendar structure and event details for a given year."""
    cal.setfirstweekday(cal.SUNDAY)

    with get_session() as session:
        # Fetch all events for the year with polls and tournaments
        # Use COALESCE to fall back to Event fields when Tournament is null
        # (Other Tournaments don't have Tournament records)
        from sqlalchemy import func

        tournament_events = (
            session.query(
                Event.id.label("event_id"),
                Event.date,
                Event.name,
                Event.event_type,
                Event.description,
                Poll.id.label("poll_id"),
                Poll.title.label("poll_title"),
                Poll.starts_at,
                Poll.closes_at,
                Poll.closed,
                Tournament.id.label("tournament_id"),
                Tournament.complete.label("tournament_complete"),
                func.coalesce(Tournament.lake_name, Event.lake_name).label("lake_name"),
                func.coalesce(Tournament.ramp_name, Event.ramp_name).label("ramp_name"),
                func.coalesce(Tournament.start_time, Event.start_time).label("start_time"),
                func.coalesce(Tournament.end_time, Event.weigh_in_time).label("end_time"),
            )
            .outerjoin(Poll, Event.id == Poll.event_id)
            .outerjoin(Tournament, Event.id == Tournament.event_id)
            .filter(extract("year", Event.date) == year)
            .order_by(Event.date)
            .all()
        )

        all_events: Dict[int, Dict[int, List[Dict[str, str]]]] = {}
        event_details: Dict[str, List[Dict[str, Any]]] = {}
        event_types_present: Set[str] = set()

        # Process events and build data structures
        for event in tournament_events:
            date_obj = datetime.combine(event.date, datetime.min.time())
            day, month = date_obj.day, date_obj.month
            event_key = f"{date_obj.month}-{date_obj.day}"
            event_type = event.event_type

            # Track events by month and day for calendar markers
            if month not in all_events:
                all_events[month] = {}
            if day not in all_events[month]:
                all_events[month][day] = []
            all_events[month][day].append({"type": event_type, "title": event.name})
            event_types_present.add(event_type)

            # Build event details with poll/tournament status
            from core.helpers.timezone import now_local

            now, event_date = now_local().date(), date_obj.date()
            poll_id, poll_closed = event.poll_id, event.closed
            tournament_id, tournament_complete = event.tournament_id, event.tournament_complete

            poll_status, poll_link, tournament_link = None, None, None

            if poll_id:
                if event_date > now:
                    poll_status = "active" if not poll_closed else "closed"
                    poll_link = f"/polls#{poll_id}"
                else:
                    poll_status, poll_link = "results", f"/polls#{poll_id}"

            if tournament_id and tournament_complete:
                tournament_link = f"/tournaments/{tournament_id}"

            if event_key not in event_details:
                event_details[event_key] = []

            event_details[event_key].append(
                {
                    "title": event.name,
                    "type": event_type,
                    "description": event.description if event.description else "",
                    "date": event.date,
                    "event_id": event.event_id,
                    "poll_id": poll_id,
                    "poll_status": poll_status,
                    "poll_link": poll_link,
                    "tournament_id": tournament_id,
                    "tournament_complete": tournament_complete,
                    "tournament_link": tournament_link,
                    "lake_name": event.lake_name if event.lake_name else None,
                    "ramp_name": event.ramp_name if event.ramp_name else None,
                    "start_time": event.start_time.strftime("%I:%M %p")
                    if event.start_time
                    else None,
                    "end_time": event.end_time.strftime("%I:%M %p") if event.end_time else None,
                }
            )

    # Build calendar structure with event markers
    calendar_structure = build_calendar_structure(year, all_events)

    return calendar_structure, event_details, event_types_present
