"""Calendar data fetching and processing."""

import calendar as cal
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from routes.dependencies import db
from routes.pages.calendar_structure import build_calendar_structure


def get_year_calendar_data(year: int) -> Tuple[List[Any], Dict[str, Any], Set[str]]:
    """Get calendar structure and event details for a given year."""
    cal.setfirstweekday(cal.SUNDAY)

    # Fetch all events for the year
    tournament_events = db(
        "SELECT e.id as event_id, e.date, e.name, e.event_type, e.description, "
        "p.id as poll_id, p.title as poll_title, p.starts_at, p.closes_at, p.closed, "
        "t.id as tournament_id, t.complete as tournament_complete "
        "FROM events e "
        "LEFT JOIN polls p ON e.id = p.event_id "
        "LEFT JOIN tournaments t ON e.id = t.event_id "
        "WHERE EXTRACT(YEAR FROM e.date) = :year "
        "ORDER BY e.date",
        {"year": str(year)},
    )

    all_events: Dict[int, Dict[int, List[Dict[str, str]]]] = {}
    event_details: Dict[str, List[Dict[str, Any]]] = {}
    event_types_present: Set[str] = set()

    # Process events and build data structures
    for event in tournament_events:
        date_obj = datetime.combine(event[1], datetime.min.time())
        day, month = date_obj.day, date_obj.month
        event_key = f"{date_obj.month}-{date_obj.day}"
        event_type = event[3]

        # Track events by month and day for calendar markers
        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []
        all_events[month][day].append({"type": event_type, "title": event[2]})
        event_types_present.add(event_type)

        # Build event details with poll/tournament status
        now, event_date = datetime.now().date(), date_obj.date()
        poll_id, poll_closed = event[5], event[9]
        tournament_id, tournament_complete = event[10], event[11]

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
                "title": event[2],
                "type": event_type,
                "description": event[4] if event[4] else "",
                "date": event[1],
                "event_id": event[0],
                "poll_id": poll_id,
                "poll_status": poll_status,
                "poll_link": poll_link,
                "tournament_id": tournament_id,
                "tournament_complete": tournament_complete,
                "tournament_link": tournament_link,
            }
        )

    # Build calendar structure with event markers
    calendar_structure = build_calendar_structure(year, all_events)

    return calendar_structure, event_details, event_types_present
