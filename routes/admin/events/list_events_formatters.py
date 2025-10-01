from typing import List


def format_upcoming_events(events: List[tuple]) -> List[dict]:
    return [
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
        for e in events
    ]


def format_past_events(events: List[tuple]) -> List[dict]:
    return [
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
        for e in events
    ]
