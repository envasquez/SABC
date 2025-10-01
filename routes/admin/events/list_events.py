from fastapi import APIRouter, Request

from core.helpers.auth import require_admin
from routes.admin.events.list_events_formatters import format_past_events, format_upcoming_events
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/admin/events")
async def admin_events(
    request: Request,
    upcoming_page: int = 1,
    past_page: int = 1,
    success: str = None,
    error: str = None,
    warnings: str = None,
):
    user = require_admin(request)
    per_page = 20
    upcoming_offset = (upcoming_page - 1) * per_page
    past_offset = (past_page - 1) * per_page
    total_upcoming = db("SELECT COUNT(*) FROM events WHERE date >= CURRENT_DATE")[0][0]
    total_past = db(
        "SELECT COUNT(*) FROM events WHERE date < CURRENT_DATE AND event_type != 'holiday'"
    )[0][0]
    events_raw = db(
        {"limit": per_page, "offset": upcoming_offset},
    )
    events_list = format_upcoming_events(events_raw)
    past_events_raw = db(
        {"limit": per_page, "offset": past_offset},
    )
    past_events = format_past_events(past_events_raw)
    upcoming_total_pages = (total_upcoming + per_page - 1) // per_page
    past_total_pages = (total_past + per_page - 1) // per_page
    return templates.TemplateResponse(
        "admin/events.html",
        {
            "request": request,
            "user": user,
            "events": events_list,
            "past_events": past_events,
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
            "success": success,
            "error": error,
            "warnings": warnings,
        },
    )
