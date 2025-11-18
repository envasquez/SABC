"""Event-related helper functions."""

import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from core.db_schema import Event, engine, get_session
from core.helpers.timezone import now_local
from core.query_service import QueryService


def get_admin_events_data(
    upcoming_page: int = 1, past_page: int = 1, per_page: int = 20
) -> Dict[str, Any]:
    """Get events data for admin page with pagination.

    Args:
        upcoming_page: Page number for upcoming events
        past_page: Page number for past events
        per_page: Number of events per page

    Returns:
        Dictionary containing upcoming and past events with counts
    """
    upcoming_offset = (upcoming_page - 1) * per_page
    past_offset = (past_page - 1) * per_page
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_admin_events_data(per_page, upcoming_offset, per_page, past_offset)


def validate_event_data(
    date_str: str,
    name: str,
    event_type: str,
    start_time: Optional[str] = None,
    weigh_in_time: Optional[str] = None,
    entry_fee: Optional[float] = None,
    lake_name: Optional[str] = None,
) -> Dict[str, List[str]]:
    """Validate event data before creation/update.

    Args:
        date_str: Event date in YYYY-MM-DD format
        name: Event name
        event_type: Type of event (sabc_tournament, holiday, other_tournament)
        start_time: Start time in HH:MM format
        weigh_in_time: Weigh-in time in HH:MM format
        entry_fee: Entry fee amount
        lake_name: Lake name (required for other tournaments)

    Returns:
        Dictionary with 'errors' and 'warnings' lists
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Validate date format
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        errors.append(f"Invalid date format: {date_str}. Expected YYYY-MM-DD")
        return {"errors": errors, "warnings": warnings}

    if date_obj.date() < now_local().date():
        warnings.append(f"Creating event for past date: {date_str}")

    with get_session() as session:
        existing = session.query(Event.id, Event.name).filter(Event.date == date_obj.date()).first()
        if existing:
            warnings.append(f"Date {date_str} already has event: {existing[1]}")

    if not name or len(name.strip()) < 3:
        errors.append("Event name must be at least 3 characters")
    if event_type == "sabc_tournament":
        if start_time and not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", start_time):
            errors.append("Invalid start time format. Use HH:MM (24-hour)")
        if weigh_in_time and not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", weigh_in_time):
            errors.append("Invalid weigh-in time format. Use HH:MM (24-hour)")
        if start_time and weigh_in_time:
            start = datetime.strptime(start_time, "%H:%M").time()
            weigh_in = datetime.strptime(weigh_in_time, "%H:%M").time()
            if weigh_in <= start:
                errors.append("Weigh-in time must be after start time")
        if entry_fee is not None and entry_fee < 0:
            errors.append("Entry fee cannot be negative")
    elif event_type == "holiday":
        if start_time or weigh_in_time or entry_fee:
            warnings.append("Holidays don't typically need tournament details")
    elif event_type == "other_tournament":
        if not lake_name or len(lake_name.strip()) < 2:
            errors.append("Lake name is required for other tournaments")
        if start_time and not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", start_time):
            errors.append("Invalid start time format. Use HH:MM (24-hour)")
        if weigh_in_time and not re.match(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$", weigh_in_time):
            errors.append("Invalid weigh-in time format. Use HH:MM (24-hour)")
        if start_time and weigh_in_time:
            start = datetime.strptime(start_time, "%H:%M").time()
            weigh_in = datetime.strptime(weigh_in_time, "%H:%M").time()
            if weigh_in <= start:
                errors.append("Weigh-in time must be after start time")
    return {"errors": errors, "warnings": warnings}
