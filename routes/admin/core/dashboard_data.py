from typing import Any, Dict, List

from routes.admin.core.event_queries import get_past_events_data, get_upcoming_events_data
from routes.dependencies import db, get_admin_anglers_list


def get_users_data() -> Dict[str, Any]:
    users = get_admin_anglers_list()
    return {
        "users": users,
        "member_count": sum(1 for u in users if u.get("member")),
        "guest_count": sum(1 for u in users if not u.get("member")),
        "total_count": len(users),
    }


def get_tournaments_data() -> List[Dict[str, Any]]:
    tournaments_raw = db(
        """SELECT t.id, t.event_id, e.date, e.name, t.lake_name, t.ramp_name,
           t.entry_fee, t.complete, t.fish_limit,
           COUNT(DISTINCT r.id) as result_count,
           COUNT(DISTINCT tr.id) as team_result_count
           FROM tournaments t
           JOIN events e ON t.event_id = e.id
           LEFT JOIN results r ON t.id = r.tournament_id
           LEFT JOIN team_results tr ON t.id = tr.tournament_id
           GROUP BY t.id
           ORDER BY e.date DESC"""
    )
    return [
        {
            "id": t[0],
            "event_id": t[1],
            "date": t[2],
            "name": t[3],
            "lake_name": t[4],
            "ramp_name": t[5],
            "entry_fee": t[6],
            "complete": bool(t[7]),
            "fish_limit": t[8],
            "result_count": t[9],
            "team_result_count": t[10],
            "total_participants": t[9] + t[10],
        }
        for t in tournaments_raw
    ]


__all__ = [
    "get_upcoming_events_data",
    "get_past_events_data",
    "get_users_data",
    "get_tournaments_data",
]
