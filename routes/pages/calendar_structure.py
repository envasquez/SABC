"""Calendar structure building functions."""

import calendar as cal
from typing import Any, Dict, List


def build_calendar_structure(
    year: int, all_events: Dict[int, Dict[int, List[Dict[str, str]]]]
) -> List[List[Any]]:
    """Build the visual calendar structure with event markers."""
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]

    calendar_structure = []

    for month_idx, month_name in enumerate(months, 1):
        weeks = []
        for week in cal.monthcalendar(year, month_idx):
            week_days = []
            for day in week:
                if day == 0:
                    week_days.append("")
                else:
                    day_str = add_event_marker(month_idx, day, all_events)
                    week_days.append(day_str)
            weeks.append(week_days)
        calendar_structure.append([month_name, weeks])

    return calendar_structure


def add_event_marker(
    month: int, day: int, all_events: Dict[int, Dict[int, List[Dict[str, str]]]]
) -> str:
    """Add visual marker to day based on event types."""
    day_str = str(day)

    if month in all_events and day in all_events[month]:
        events_for_day = all_events[month][day]
        has_sabc = any(e["type"] == "sabc_tournament" for e in events_for_day)
        has_club_event = any(e["type"] == "club_event" for e in events_for_day)
        has_holiday = any(e["type"] == "holiday" for e in events_for_day)
        has_other = any(e["type"] == "other_tournament" for e in events_for_day)

        if has_sabc:
            day_str += "†"
        elif has_club_event:
            day_str += "§"
        elif has_other:
            day_str += "‡"
        elif has_holiday:
            day_str += "*"

    return day_str
