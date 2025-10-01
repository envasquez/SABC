from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.helpers.auth import require_admin
from routes.admin.core.dashboard_data import get_tournaments_data, get_users_data
from routes.admin.core.event_queries import get_past_events_data, get_upcoming_events_data
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
        past_events, total_past = get_past_events_data(past_page, per_page)
        ctx["past_events"] = past_events
        upcoming_total_pages = (total_upcoming + per_page - 1) // per_page
        past_total_pages = (total_past + per_page - 1) // per_page
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
