"""Admin events routes - event management and bulk operations."""

import calendar
from datetime import date, timedelta

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from routes.dependencies import (
    admin,
    db,
    get_federal_holidays,
)

from fastapi import APIRouter

router = APIRouter()


@router.get("/admin/federal-holidays/{year}")
async def get_federal_holidays_api(request: Request, year: int):
    """API endpoint to get federal holidays for a year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        holidays = get_federal_holidays(year)
        return JSONResponse({"holidays": holidays})
    except Exception as e:
        return JSONResponse({"error": f"Error getting holidays: {str(e)}"}, status_code=500)


@router.post("/admin/events/bulk-delete")
async def bulk_delete_events(request: Request):
    """Delete multiple events at once (only if they have no results)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        event_ids = data.get("event_ids", [])

        if not event_ids:
            return JSONResponse({"error": "No events selected"}, status_code=400)

        deleted_count = 0
        blocked_events = []

        for event_id in event_ids:
            # Check if event has results
            has_results = db(
                """
                SELECT 1 FROM tournaments t WHERE t.event_id = ?
                AND (EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id)
                     OR EXISTS(SELECT 1 FROM team_results WHERE tournament_id = t.id))
                LIMIT 1
            """,
                (event_id,),
            )

            if has_results:
                event_info = db("SELECT name, date FROM events WHERE id = :id", {"id": event_id})
                if event_info:
                    blocked_events.append(f"{event_info[0][0]} ({event_info[0][1]})")
                continue

            # Safe to delete
            db(
                "DELETE FROM poll_votes WHERE poll_id IN (SELECT id FROM polls WHERE event_id = ?)",
                (event_id,),
            )
            db(
                "DELETE FROM poll_options WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)",
                {"event_id": event_id},
            )
            db("DELETE FROM polls WHERE event_id = :event_id", {"event_id": event_id})
            db(
                "DELETE FROM tournaments WHERE event_id = :event_id AND complete = 0",
                {"event_id": event_id},
            )
            db("DELETE FROM events WHERE id = :id", {"id": event_id})
            deleted_count += 1

        message = f"Successfully deleted {deleted_count} event(s)"
        if blocked_events:
            message += f". Could not delete {len(blocked_events)} event(s) with results"

        return JSONResponse(
            {
                "success": True,
                "deleted_count": deleted_count,
                "blocked_count": len(blocked_events),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Bulk delete failed: {str(e)}"}, status_code=500)


@router.post("/admin/events/bulk-create-holidays")
async def bulk_create_holidays(request: Request):
    """Create federal holidays for a given year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        year = data.get("year")

        if not year or not (2020 <= year <= 2030):
            return JSONResponse(
                {"error": "Invalid year. Must be between 2020 and 2030"}, status_code=400
            )

        holidays = get_federal_holidays(year)
        created_count = 0
        skipped_holidays = []

        for holiday_date, holiday_name in holidays:
            existing = db("SELECT id FROM events WHERE date = :date", {"date": holiday_date})
            if existing:
                skipped_holidays.append(f"{holiday_name} ({holiday_date})")
                continue

            db(
                """
                INSERT INTO events (date, year, name, event_type, description, holiday_name)
                VALUES (?, ?, ?, 'federal_holiday', ?, ?)
            """,
                (
                    holiday_date,
                    year,
                    holiday_name,
                    f"Federal holiday: {holiday_name}",
                    holiday_name,
                ),
            )
            created_count += 1

        message = f"Created {created_count} federal holiday(s) for {year}"
        if skipped_holidays:
            message += f". Skipped {len(skipped_holidays)} existing"

        return JSONResponse(
            {
                "success": True,
                "created_count": created_count,
                "skipped_count": len(skipped_holidays),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Holiday creation failed: {str(e)}"}, status_code=500)


@router.post("/admin/events/bulk-create-tournaments")
async def bulk_create_tournaments(request: Request):
    """Create monthly tournaments for a year."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        year = data.get("year")
        start_month = data.get("start_month", 1)
        end_month = data.get("end_month", 12)
        weekend_preference = data.get("weekend_preference", "saturday")

        if not year or not (2020 <= year <= 2030):
            return JSONResponse(
                {"error": "Invalid year. Must be between 2020 and 2030"}, status_code=400
            )

        if not (1 <= start_month <= 12) or not (1 <= end_month <= 12) or start_month > end_month:
            return JSONResponse({"error": "Invalid month range"}, status_code=400)

        created_count = 0
        skipped_months = []

        for month in range(start_month, end_month + 1):
            first_day = date(year, month, 1)
            target_weekday = 5 if weekend_preference == "saturday" else 6
            days_to_target = (target_weekday - first_day.weekday()) % 7
            first_target = first_day + timedelta(days=days_to_target)
            tournament_date = first_target + timedelta(days=14)  # 3rd occurrence

            if tournament_date.month != month:
                tournament_date = first_target + timedelta(days=7)  # 2nd occurrence

            tournament_date_str = tournament_date.strftime("%Y-%m-%d")

            existing = db("SELECT id FROM events WHERE date = :date", {"date": tournament_date_str})
            if existing:
                month_name = calendar.month_name[month]
                skipped_months.append(f"{month_name} ({tournament_date_str})")
                continue

            month_name = calendar.month_name[month]
            tournament_name = f"{month_name} {year} Tournament"

            db(
                """
                INSERT INTO events (date, year, name, event_type, description,
                                  start_time, weigh_in_time, entry_fee)
                VALUES (?, ?, ?, 'sabc_tournament', ?, '06:00', '15:00', 25.00)
            """,
                (
                    tournament_date_str,
                    year,
                    tournament_name,
                    f"SABC monthly tournament for {month_name} {year}",
                ),
            )
            created_count += 1

        message = f"Created {created_count} tournament(s) for {year}"
        if skipped_months:
            message += f". Skipped {len(skipped_months)} months with existing events"

        return JSONResponse(
            {
                "success": True,
                "created_count": created_count,
                "skipped_count": len(skipped_months),
                "message": message,
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Tournament creation failed: {str(e)}"}, status_code=500)
