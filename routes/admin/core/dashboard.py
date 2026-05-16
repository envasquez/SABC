from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy import Date, Integer, cast, func

from core.db_schema import Event, Poll, get_session
from core.helpers.auth import require_admin
from core.helpers.pagination import PaginationState
from core.helpers.timezone import now_local
from routes.admin.core.dashboard_data import get_tournaments_data, get_users_data
from routes.admin.core.event_queries import get_sabc_tournaments, get_upcoming_events_data
from routes.dependencies import templates

router = APIRouter()

# Valid admin pages
VALID_ADMIN_PAGES = {"events", "users", "tournaments"}


@router.get("/admin")
async def admin_root(request: Request) -> RedirectResponse:
    _user = require_admin(request)
    return RedirectResponse("/admin/events", status_code=303)


@router.get("/admin/{page}")
async def admin_page(
    request: Request, page: str, upcoming_page: int = 1, past_page: int = 1
) -> Response:
    user = require_admin(request)

    # Validate page parameter
    if page not in VALID_ADMIN_PAGES:
        raise HTTPException(status_code=404, detail=f"Admin page '{page}' not found")

    current_year = now_local().year
    ctx: Dict[str, Any] = {"user": user, "current_year": current_year}
    if page == "events":
        per_page = 20
        events, total_upcoming = get_upcoming_events_data(upcoming_page, per_page)
        ctx["events"] = events

        # Get ALL past and upcoming SABC tournaments (no pagination for client-side filtering)
        past_tournaments = get_sabc_tournaments("past")
        upcoming_sabc_tournaments = get_sabc_tournaments("upcoming")

        with get_session() as session:
            # Get years for Past Tournaments tab filter
            year_col = func.extract("year", Event.date).cast(Integer)
            past_tournament_years_query = (
                session.query(year_col.label("year"))
                .filter(
                    Event.date < cast(func.current_date(), Date),
                    Event.event_type == "sabc_tournament",
                )
                .distinct()
                .order_by(year_col.desc())
                .all()
            )
            past_tournament_years = [int(row[0]) for row in past_tournament_years_query]

            # Get unique lakes for Past Tournaments tab filter
            past_tournament_lakes_query = (
                session.query(Event.lake_name)
                .filter(
                    Event.date < cast(func.current_date(), Date),
                    Event.event_type == "sabc_tournament",
                    Event.lake_name.isnot(None),
                )
                .distinct()
                .order_by(Event.lake_name)
                .all()
            )
            past_tournament_lakes = [row[0] for row in past_tournament_lakes_query if row[0]]

            # Get tournament polls for the poll dropdown (exclude generic/club polls)
            # Use outerjoin to include polls without event_id
            available_polls_query = (
                session.query(Poll.id, Poll.title, Event.date, Event.name)
                .outerjoin(Event, Poll.event_id == Event.id)
                .filter(Poll.poll_type != "generic")
                .order_by(Event.date.desc().nullslast())
                .all()
            )
            available_polls = [
                {
                    "id": p[0],
                    "title": p[1],
                    "event_date": p[2] if p[2] else None,
                    "event_name": p[3] if p[3] else "",
                }
                for p in available_polls_query
            ]

        ctx["past_tournaments"] = past_tournaments
        ctx["upcoming_sabc_tournaments"] = upcoming_sabc_tournaments
        ctx["past_tournament_years"] = past_tournament_years
        ctx["past_tournament_lakes"] = past_tournament_lakes
        ctx["available_polls"] = available_polls

        upcoming_pagination = PaginationState(
            page=upcoming_page, items_per_page=per_page, total_items=total_upcoming
        )
        # Past tournaments don't use pagination - all loaded for client-side filtering
        total_past = len(past_tournaments)
        past_pagination = PaginationState(
            page=past_page, items_per_page=total_past or 1, total_items=total_past
        )
        ctx.update(upcoming_pagination.to_template_context(prefix="upcoming"))
        ctx.update(past_pagination.to_template_context(prefix="past"))
        ctx.update(
            {
                "total_upcoming": total_upcoming,
                "total_past": total_past,
                "per_page": per_page,
            }
        )
    elif page == "users":
        ctx.update(get_users_data())
    elif page == "tournaments":
        ctx["tournaments"] = get_tournaments_data()
    return templates.TemplateResponse(request, f"admin/{page}.html", ctx)
