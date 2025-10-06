from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from routes.admin.core.dashboard_data import get_tournaments_data, get_users_data
from routes.admin.core.event_queries import get_upcoming_events_data
from routes.dependencies import db, templates

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

        # Get ALL past tournaments for Past Tournaments tab (no pagination for client-side filtering)
        past_tournaments_raw = db(
            """SELECT e.id, e.date, e.name, e.description, e.event_type,
               e.entry_fee, e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
               EXISTS(SELECT 1 FROM polls WHERE event_id = e.id) as has_poll,
               EXISTS(SELECT 1 FROM tournaments WHERE event_id = e.id) as has_tournament,
               COALESCE(t.complete, FALSE) as tournament_complete,
               EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id) as has_results
               FROM events e
               LEFT JOIN tournaments t ON e.id = t.event_id
               WHERE e.date < CURRENT_DATE AND e.event_type = 'sabc_tournament'
               ORDER BY e.date DESC"""
        )
        past_tournaments = (
            [
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
                for e in past_tournaments_raw
            ]
            if past_tournaments_raw
            else []
        )
        ctx["past_tournaments"] = past_tournaments

        # Get years for Past Tournaments tab filter
        past_tournament_years_raw = db(
            "SELECT DISTINCT EXTRACT(YEAR FROM date)::int as year FROM events WHERE date < CURRENT_DATE AND event_type = 'sabc_tournament' ORDER BY year DESC"
        )
        past_tournament_years = (
            [int(row[0]) for row in past_tournament_years_raw] if past_tournament_years_raw else []
        )
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
