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
        {"limit": per_page, "offset": upcoming_offset},
    )
    events_list = format_upcoming_events(events_raw)
    past_events_raw = db(
        """SELECT e.id, e.date, e.name, e.description, e.event_type,
           e.entry_fee, e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
           EXISTS(SELECT 1 FROM polls WHERE event_id = e.id) as has_poll,
           EXISTS(SELECT 1 FROM tournaments WHERE event_id = e.id) as has_tournament,
           COALESCE(t.complete, FALSE) as tournament_complete,
           EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id) as has_results
           FROM events e
           LEFT JOIN tournaments t ON e.id = t.event_id
           WHERE e.date < CURRENT_DATE AND e.event_type != 'holiday'
           ORDER BY e.date DESC
           LIMIT :limit OFFSET :offset""",
        {"limit": per_page, "offset": past_offset},
    )
    past_events = format_past_events(past_events_raw)
    upcoming_total_pages = (total_upcoming + per_page - 1) // per_page
    past_total_pages = (total_past + per_page - 1) // per_page
    # Get past event years
    past_years_raw = db(
        "SELECT DISTINCT EXTRACT(YEAR FROM date)::int as year FROM events WHERE date < CURRENT_DATE AND event_type != 'holiday' ORDER BY year DESC"
    )
    past_years = [int(row[0]) for row in past_years_raw] if past_years_raw else []
    return templates.TemplateResponse(
        "admin/events.html",
        {
            "request": request,
            "user": user,
            "events": events_list,
            "past_events": past_events,
            "past_years": past_years,
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
