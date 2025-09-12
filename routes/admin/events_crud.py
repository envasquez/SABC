"""Admin events CRUD routes - create, read, update, delete individual events."""

import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import text

from routes.dependencies import (
    admin,
    db,
    engine,
    find_lake_data_by_db_name,
    get_lakes_list,
    validate_event_data,
)

router = APIRouter()


@router.post("/admin/events/create")
async def create_event(
    request: Request,
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(default="sabc_tournament"),
    description: str = Form(default=""),
    start_time: str = Form(default="06:00"),
    weigh_in_time: str = Form(default="15:00"),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
):
    """Create a new event and optionally auto-create poll for SABC tournaments."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Validate input data
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee
        )

        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )

        warning_msg = ""
        if validation["warnings"]:
            warning_msg = f"&warnings={'; '.join(validation['warnings'])}"

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year

        params = {
            "date": date,
            "year": year,
            "name": name,
            "event_type": event_type,
            "description": description,
            "start_time": start_time if event_type == "sabc_tournament" else None,
            "weigh_in_time": weigh_in_time if event_type == "sabc_tournament" else None,
            "lake_name": lake_name if lake_name else None,
            "ramp_name": ramp_name if ramp_name else None,
            "entry_fee": entry_fee if event_type == "sabc_tournament" else None,
            "holiday_name": name if event_type == "holiday" else None,
        }

        event_id = db(
            """
            INSERT INTO events (date, year, name, event_type, description,
                              start_time, weigh_in_time, lake_name, ramp_name,
                              entry_fee, holiday_name)
            VALUES (:date, :year, :name, :event_type, :description,
                   :start_time, :weigh_in_time, :lake_name, :ramp_name,
                   :entry_fee, :holiday_name)
        """,
            params,
        )

        # Auto-create poll for SABC tournaments
        if event_type == "sabc_tournament":
            poll_starts = (date_obj - timedelta(days=7)).isoformat()
            poll_closes = (date_obj - timedelta(days=5)).isoformat()

            poll_id = db(
                """
                INSERT INTO polls (title, description, poll_type, event_id, created_by,
                                 starts_at, closes_at, closed, multiple_votes)
                VALUES (:title, :description, 'tournament_location', :event_id, :created_by,
                       :starts_at, :closes_at, 0, 0)
            """,
                {
                    "title": name,
                    "description": description if description else f"Vote for location for {name}",
                    "event_id": event_id,
                    "created_by": user["id"],
                    "starts_at": poll_starts,
                    "closes_at": poll_closes,
                },
            )

            # Add all lakes as poll options
            all_lakes = get_lakes_list()
            for lake_id, lake_name, location in all_lakes:
                option_data = {"lake_id": lake_id}
                db(
                    """
                    INSERT INTO poll_options (poll_id, option_text, option_data)
                    VALUES (:poll_id, :option_text, :option_data)
                """,
                    {
                        "poll_id": poll_id,
                        "option_text": lake_name,
                        "option_data": json.dumps(option_data),
                    },
                )

        return RedirectResponse(
            f"/admin/events?success=Event created successfully{warning_msg}", status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to create event: {str(e)}", status_code=302
        )


@router.get("/admin/events/{event_id}/info")
async def get_event_info(request: Request, event_id: int):
    """Get complete event information (for edit modal)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        event_info = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type,
                   e.start_time, e.weigh_in_time,
                   COALESCE(t.lake_name, e.lake_name) as lake_name,
                   COALESCE(t.ramp_name, e.ramp_name) as ramp_name,
                   e.entry_fee, e.holiday_name,
                   p.closes_at, p.starts_at, p.id as poll_id, p.closed,
                   t.id as tournament_id
            FROM events e
            LEFT JOIN polls p ON p.event_id = e.id
            LEFT JOIN tournaments t ON t.event_id = e.id
            WHERE e.id = :event_id ORDER BY p.id DESC LIMIT 1
        """,
            {"event_id": event_id},
        )

        if event_info:
            event = event_info[0]
            lake_display_name = event[7] or ""
            if lake_display_name:
                yaml_key, lake_info, display_name = find_lake_data_by_db_name(lake_display_name)
                if display_name:
                    lake_display_name = display_name

            return JSONResponse(
                {
                    "id": event[0],
                    "date": event[1],
                    "name": event[2],
                    "description": event[3] or "",
                    "event_type": event[4],
                    "start_time": event[5],
                    "weigh_in_time": event[6],
                    "lake_name": lake_display_name,
                    "ramp_name": event[8] or "",
                    "entry_fee": event[9],
                    "holiday_name": event[10] or "",
                    "poll_closes_at": event[11],
                    "poll_starts_at": event[12],
                    "poll_id": event[13],
                    "poll_closed": bool(event[14]) if event[14] is not None else None,
                    "tournament_id": event[15],
                }
            )
        else:
            return JSONResponse({"error": "Event not found"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": f"Failed to get event info: {str(e)}"}, status_code=500)


@router.post("/admin/events/validate")
async def validate_event(request: Request):
    """Validate event data without creating."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        data = await request.json()
        validation = validate_event_data(
            data.get("date", ""),
            data.get("name", ""),
            data.get("event_type", ""),
            data.get("start_time", ""),
            data.get("weigh_in_time", ""),
            data.get("entry_fee", 0),
        )
        return JSONResponse(validation)
    except Exception as e:
        return JSONResponse({"error": f"Validation failed: {str(e)}"}, status_code=500)


@router.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int):
    """Delete an event (only if no results exist)."""
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)

    try:
        # Check if event has results
        has_results = db(
            """
            SELECT 1 FROM tournaments t WHERE t.event_id = :event_id
            AND (EXISTS(SELECT 1 FROM results WHERE tournament_id = t.id)
                 OR EXISTS(SELECT 1 FROM team_results WHERE tournament_id = t.id))
            LIMIT 1
        """,
            {"event_id": event_id},
        )

        if has_results:
            return JSONResponse(
                {"error": "Cannot delete event with tournament results"}, status_code=400
            )

        # Delete cascade: polls -> tournaments -> event
        with engine.begin() as conn:
            conn.execute(
                text(
                    "DELETE FROM poll_votes WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )
            conn.execute(
                text(
                    "DELETE FROM poll_options WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )
            conn.execute(
                text("DELETE FROM polls WHERE event_id = :event_id"), {"event_id": event_id}
            )
            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            conn.commit()

        return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
