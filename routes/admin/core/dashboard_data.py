from typing import Any, Dict, List

from sqlalchemy import func

from core.db_schema import Event, Result, TeamResult, Tournament, get_session
from routes.admin.core.event_queries import get_past_events_data, get_upcoming_events_data
from routes.dependencies import get_admin_anglers_list


def get_users_data() -> Dict[str, Any]:
    users = get_admin_anglers_list()
    return {
        "users": users,
        "member_count": sum(1 for u in users if u.get("member")),
        "guest_count": sum(1 for u in users if not u.get("member")),
        "total_count": len(users),
    }


def get_tournaments_data() -> List[Dict[str, Any]]:
    with get_session() as session:
        tournaments_query = (
            session.query(
                Tournament.id,
                Tournament.event_id,
                Event.date,
                Event.name,
                Tournament.lake_name,
                Tournament.ramp_name,
                Tournament.entry_fee,
                Tournament.complete,
                Tournament.fish_limit,
                func.count(func.distinct(Result.id)).label("result_count"),
                func.count(func.distinct(TeamResult.id)).label("team_result_count"),
            )
            .join(Event, Tournament.event_id == Event.id)
            .outerjoin(Result, Tournament.id == Result.tournament_id)
            .outerjoin(TeamResult, Tournament.id == TeamResult.tournament_id)
            .group_by(Tournament.id, Event.date, Event.name)
            .order_by(Event.date.desc())
            .all()
        )

        tournaments = [
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
            for t in tournaments_query
        ]

    return tournaments


__all__ = [
    "get_upcoming_events_data",
    "get_past_events_data",
    "get_users_data",
    "get_tournaments_data",
]
