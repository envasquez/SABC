from typing import Any, Dict, List

from routes.dependencies import db


def get_upcoming_events_data(page: int, per_page: int) -> tuple[List[Dict[str, Any]], int]:
    offset = (page - 1) * per_page
    total = db("SELECT COUNT(*) FROM events WHERE date >= CURRENT_DATE")[0][0]
    events_raw = db(
        """SELECT e.id, e.date, e.name, e.description, e.event_type, e.year,
           EXTRACT(DOW FROM e.date) as day_num,
           EXISTS(SELECT 1 FROM polls WHERE event_id = e.id) as has_poll,
           EXISTS(SELECT 1 FROM tournaments WHERE event_id = e.id) as has_tournament,
           EXISTS(SELECT 1 FROM polls WHERE event_id = e.id AND closed = FALSE) as poll_active,
           e.start_time, e.weigh_in_time, e.entry_fee, e.lake_name, e.ramp_name, e.holiday_name,
           COALESCE(t.complete, FALSE) as tournament_complete
           FROM events e
           LEFT JOIN tournaments t ON e.id = t.event_id
           WHERE e.date >= CURRENT_DATE
           ORDER BY e.date
           LIMIT :limit OFFSET :offset""",
        {"limit": per_page, "offset": offset},
    )
    events = [
        {
            "id": e[0],
            "date": e[1],
            "name": e[2] or "",
            "description": e[3] or "",
            "event_type": e[4] or "sabc_tournament",
            "day_name": e[6],
            "has_poll": bool(e[7]),
            "has_tournament": bool(e[8]),
            "poll_active": bool(e[9]),
            "start_time": e[10],
            "weigh_in_time": e[11],
            "entry_fee": e[12],
            "lake_name": e[13],
            "ramp_name": e[14],
            "holiday_name": e[15],
            "tournament_complete": bool(e[16]),
        }
        for e in events_raw
    ]
    return events, total


def get_past_events_data(page: int, per_page: int) -> tuple[List[Dict[str, Any]], int]:
    offset = (page - 1) * per_page
    total = db(
        "SELECT COUNT(*) FROM events WHERE date < CURRENT_DATE AND event_type = 'sabc_tournament'"
    )[0][0]
    past_events_raw = db(
        """SELECT e.id, e.date, e.name, e.description, e.event_type,
           e.entry_fee, e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
           EXISTS(SELECT 1 FROM polls WHERE event_id = e.id) as has_poll,
           EXISTS(SELECT 1 FROM tournaments WHERE event_id = e.id) as has_tournament,
           COALESCE(t.complete, FALSE) as tournament_complete,
           EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id) as has_results
           FROM events e
           LEFT JOIN tournaments t ON e.id = t.event_id
           WHERE e.date < CURRENT_DATE AND e.event_type = 'sabc_tournament'
           ORDER BY e.date DESC
           LIMIT :limit OFFSET :offset""",
        {"limit": per_page, "offset": offset},
    )
    past_events = [
        {
            "id": e[0],
            "date": e[1],
            "name": e[2] or "",
            "description": e[3] or "",
            "event_type": e[4] or "sabc_tournament",
            "entry_fee": e[5],
            "lake_name": e[6],
            "start_time": e[7],
            "weigh_in_time": e[8],
            "holiday_name": e[9],
            "has_poll": bool(e[10]),
            "has_tournament": bool(e[11]),
            "tournament_complete": bool(e[12]),
            "has_results": bool(e[13]),
        }
        for e in past_events_raw
    ]
    return past_events, total
