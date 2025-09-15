import calendar
from datetime import datetime


def build_calendar_data_with_polls(calendar_events, tournament_events, year=None):
    if year is None:
        year = datetime.now().year
    # Set Sunday as the first day of the week to match US calendar convention
    calendar.setfirstweekday(calendar.SUNDAY)

    # Combine all events and store detailed event info
    all_events = {}
    event_details = {}  # Store detailed event info for modal display
    event_types_present = set()  # Track which event types exist

    # Add calendar events (event_date, title, event_type, description)
    for event in calendar_events:
        date_obj = datetime.strptime(event[0], "%Y-%m-%d")
        day = date_obj.day
        month = date_obj.month
        event_type = event[2]
        event_key = f"{month}-{day}"

        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []

        all_events[month][day].append({"type": event_type, "title": event[1]})
        event_types_present.add(event_type)

        # Store detailed event info
        if event_key not in event_details:
            event_details[event_key] = []
        event_details[event_key].append(
            {
                "title": event[1],
                "type": event_type,
                "description": event[3] if event[3] else "",
                "date": event[0],
            }
        )

    # Add tournament events with poll/tournament information
    # tournament_events columns: event_id, date, name, event_type, description, poll_id, poll_title, starts_at, closes_at, closed, tournament_id, tournament_complete
    for event in tournament_events:
        date_obj = datetime.strptime(event[1], "%Y-%m-%d")  # event[1] is date
        day = date_obj.day
        month = date_obj.month
        event_key = f"{month}-{day}"
        event_type = event[3]  # event[3] is event_type

        if month not in all_events:
            all_events[month] = {}
        if day not in all_events[month]:
            all_events[month][day] = []

        all_events[month][day].append(
            {
                "type": event_type,
                "title": event[2],  # event[2] is name
            }
        )
        event_types_present.add(event_type)

        # Determine poll status for the event
        now = datetime.now().date()
        event_date = date_obj.date()
        poll_id = event[5]  # poll_id
        poll_closed = event[9]  # closed
        tournament_id = event[10]  # tournament_id
        tournament_complete = event[11]  # tournament_complete

        poll_status = None
        poll_link = None
        tournament_link = None

        if poll_id:
            if event_date > now:
                # Future event - check if poll is active
                if not poll_closed:
                    poll_status = "active"
                    poll_link = f"/polls#{poll_id}"
                else:
                    poll_status = "closed"
                    poll_link = f"/polls#{poll_id}"
            else:
                # Past event - show poll results
                poll_status = "results"
                poll_link = f"/polls#{poll_id}"

        # Add tournament results link if tournament exists and is complete
        if tournament_id and tournament_complete:
            # Always use local tournament view
            tournament_link = f"/tournaments/{tournament_id}"

        # Store detailed event info with poll and tournament links
        if event_key not in event_details:
            event_details[event_key] = []
        event_details[event_key].append(
            {
                "title": event[2],  # name
                "type": event_type,
                "description": event[4] if event[4] else "",  # description
                "date": event[1],  # date
                "event_id": event[0],  # event_id
                "poll_id": poll_id,
                "poll_status": poll_status,
                "poll_link": poll_link,
                "tournament_id": tournament_id,
                "tournament_complete": tournament_complete,
                "tournament_link": tournament_link,
            }
        )

    # Build the exact calendar structure expected by template
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
        # Get calendar for this month
        cal = calendar.monthcalendar(year, month_idx)

        # Build weeks structure
        weeks = []
        for week in cal:
            week_days = []
            for day in week:
                if day == 0:
                    week_days.append("")
                else:
                    day_str = str(day)

                    # Check if this day has events
                    if month_idx in all_events and day in all_events[month_idx]:
                        events_for_day = all_events[month_idx][day]

                        # Apply markers based on event types (prioritize SABC tournaments)
                        has_sabc = any(e["type"] == "sabc_tournament" for e in events_for_day)
                        has_club_event = any(e["type"] == "club_event" for e in events_for_day)
                        has_holiday = any(e["type"] == "holiday" for e in events_for_day)
                        has_other = any(e["type"] == "other_tournament" for e in events_for_day)

                        if has_sabc:
                            day_str += "†"  # Blue marker for SABC tournaments
                        elif has_club_event:
                            day_str += "§"  # Green marker for club events
                        elif has_other:
                            day_str += "‡"  # Orange marker for other tournaments
                        elif has_holiday:
                            day_str += "*"  # Red marker for holidays

                    week_days.append(day_str)

            weeks.append(week_days)

        calendar_structure.append([month_name, weeks])

    return calendar_structure, event_details, event_types_present
