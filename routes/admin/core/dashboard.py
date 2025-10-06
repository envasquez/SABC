from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import Date, cast, exists, func, select

from core.db_schema import Event, Poll, Result, Tournament, get_session
from core.helpers.auth import require_admin
from routes.admin.core.dashboard_data import get_tournaments_data, get_users_data
from routes.admin.core.event_queries import get_upcoming_events_data
from routes.dependencies import templates

router = APIRouter()


@router.get("/admin")
async def admin_root(request: Request):
    _user = require_admin(request)
    return RedirectResponse("/admin/events", status_code=302)


@router.get("/admin/{page}")
async def admin_page(request: Request, page: str, upcoming_page: int = 1, past_page: int = 1):
    user = require_admin(request)
    ctx: Dict[str, Any] = {"request": request, "user": user}
    if page == "events":
        per_page = 20
        events, total_upcoming = get_upcoming_events_data(upcoming_page, per_page)
        ctx["events"] = events

        with get_session() as session:
            # Get ALL past tournaments for Past Tournaments tab (no pagination for client-side filtering)
            past_tournaments_query = (
                session.query(
                    Event.id,
                    Event.date,
                    Event.name,
                    Event.description,
                    Event.event_type,
                    Event.entry_fee,
                    Event.lake_name,
                    Event.start_time,
                    Event.weigh_in_time,
                    Event.holiday_name,
                    exists(select(1).where(Poll.event_id == Event.id).correlate_except(Poll)).label(
                        "has_poll"
                    ),
                    exists(
                        select(1)
                        .where(Tournament.event_id == Event.id)
                        .correlate_except(Tournament)
                    ).label("has_tournament"),
                    func.coalesce(Tournament.complete, False).label("tournament_complete"),
                    exists(
                        select(1)
                        .where(Result.tournament_id == Tournament.id)
                        .correlate_except(Result)
                    ).label("has_results"),
                )
                .outerjoin(Tournament, Event.id == Tournament.event_id)
                .filter(
                    Event.date < cast(func.current_date(), Date),
                    Event.event_type == "sabc_tournament",
                )
                .order_by(Event.date.desc())
                .all()
            )

            past_tournaments = [
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
                for e in past_tournaments_query
            ]

            # Get years for Past Tournaments tab filter
            past_tournament_years_query = (
                session.query(func.extract("year", Event.date).cast(int).label("year"))
                .filter(
                    Event.date < cast(func.current_date(), Date),
                    Event.event_type == "sabc_tournament",
                )
                .distinct()
                .order_by(func.extract("year", Event.date).desc())
                .all()
            )
            past_tournament_years = [int(row[0]) for row in past_tournament_years_query]

        ctx["past_tournaments"] = past_tournaments
        ctx["past_tournament_years"] = past_tournament_years

        upcoming_total_pages = (total_upcoming + per_page - 1) // per_page
        # Past tournaments don't use pagination - all loaded for client-side filtering
        past_total_pages = 1
        total_past = len(past_tournaments)
        ctx.update(
            {
                "upcoming_page": upcoming_page,
                "upcoming_total_pages": upcoming_total_pages,
                "upcoming_has_prev": upcoming_page > 1,
                "upcoming_has_next": upcoming_page < upcoming_total_pages,
                "upcoming_prev_page": upcoming_page - 1,
                "upcoming_next_page": upcoming_page + 1,
                "total_upcoming": total_upcoming,
                "past_page": past_page,
                "past_total_pages": past_total_pages,
                "past_has_prev": past_page > 1,
                "past_has_next": past_page < past_total_pages,
                "past_prev_page": past_page - 1,
                "past_next_page": past_page + 1,
                "total_past": total_past,
                "per_page": per_page,
            }
        )
    elif page == "users":
        ctx.update(get_users_data())
    elif page == "tournaments":
        ctx["tournaments"] = get_tournaments_data()
    return templates.TemplateResponse(f"admin/{page}.html", ctx)
