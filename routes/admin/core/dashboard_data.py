from typing import Any, Dict, List

from sqlalchemy import func

from core.db_schema import Event, Result, TeamResult, Tournament, get_session
from core.db_schema.views import v_angler_tournament_results, v_team_tournament_results
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
    """Admin dashboard per-tournament summary.

    Previously computed ``total_participants = result_count + team_result_count``,
    which double-counted every team-format tournament (a tournament with
    N anglers organized into M teams reported N+M participants instead of N).
    Switched to COUNT(DISTINCT angler_id) from v_angler_tournament_results
    which is the correct angler count regardless of format.

    result_count / team_result_count are kept on the row for any template
    that still inspects them; total_participants is now the authoritative
    figure.
    """
    vatr = v_angler_tournament_results
    vttr = v_team_tournament_results
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
                # Existing raw counts kept for template back-compat.
                func.count(func.distinct(Result.id)).label("result_count"),
                func.count(func.distinct(TeamResult.id)).label("team_result_count"),
                # Correct angler count via the unified view (subquery to
                # keep it independent of the outer GROUP BY semantics).
                (
                    session.query(func.count(func.distinct(vatr.c.angler_id)))
                    .filter(vatr.c.tournament_id == Tournament.id)
                    .correlate(Tournament)
                    .scalar_subquery()
                ).label("participant_count"),
                (
                    session.query(func.count())
                    .select_from(vttr)
                    .filter(vttr.c.tournament_id == Tournament.id)
                    .correlate(Tournament)
                    .scalar_subquery()
                ).label("boat_count"),
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
                "total_participants": t[11] or 0,
                "boat_count": t[12] or 0,
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
