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
    fish_limit: int = Form(default=5),
):
    """Create a new event and optionally auto-create poll for SABC tournaments."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Validate input data
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee, lake_name
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
            "start_time": start_time
            if event_type in ["sabc_tournament", "other_tournament"]
            else None,
            "weigh_in_time": weigh_in_time
            if event_type in ["sabc_tournament", "other_tournament"]
            else None,
            "lake_name": lake_name if lake_name else None,
            "ramp_name": ramp_name if ramp_name else None,
            "entry_fee": entry_fee if event_type == "sabc_tournament" else 0.00,
            "fish_limit": fish_limit if event_type == "sabc_tournament" else None,
            "holiday_name": name if event_type == "holiday" else None,
        }

        event_id = db(
            """
            INSERT INTO events (date, year, name, event_type, description,
                              start_time, weigh_in_time, lake_name, ramp_name,
                              entry_fee, fish_limit, holiday_name)
            VALUES (:date, :year, :name, :event_type, :description,
                   :start_time, :weigh_in_time, :lake_name, :ramp_name,
                   :entry_fee, :fish_limit, :holiday_name)
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
        error_msg = str(e)

        # Handle common database constraint errors with user-friendly messages
        if "UNIQUE constraint failed: events.date" in error_msg:
            error_msg = f"An event already exists on {date}. Please choose a different date or edit the existing event."
        elif "NOT NULL constraint failed" in error_msg:
            error_msg = "Required field missing. Please fill in all required fields."
        elif "FOREIGN KEY constraint failed" in error_msg:
            error_msg = "Invalid lake or ramp selection. Please refresh the page and try again."
        else:
            # For other errors, show a generic message with details for debugging
            error_msg = f"Failed to create event. Details: {error_msg}"

        return RedirectResponse(f"/admin/events?error={error_msg}", status_code=302)


@router.post("/admin/events/edit")
async def edit_event(
    request: Request,
    event_id: int = Form(),
    date: str = Form(),
    name: str = Form(),
    event_type: str = Form(),
    description: str = Form(default=""),
    start_time: str = Form(default=""),
    weigh_in_time: str = Form(default=""),
    lake_name: str = Form(default=""),
    ramp_name: str = Form(default=""),
    entry_fee: float = Form(default=25.00),
    fish_limit: int = Form(default=5),
    poll_closes_date: str = Form(default=""),
):
    """Edit an existing event."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Validate input data
        validation = validate_event_data(
            date, name, event_type, start_time, weigh_in_time, entry_fee, lake_name
        )

        if validation["errors"]:
            error_msg = "; ".join(validation["errors"])
            return RedirectResponse(
                f"/admin/events?error=Validation failed: {error_msg}", status_code=302
            )

        date_obj = datetime.strptime(date, "%Y-%m-%d")
        year = date_obj.year

        # Update the event
        params = {
            "event_id": event_id,
            "date": date,
            "year": year,
            "name": name,
            "event_type": event_type,
            "description": description,
            "start_time": start_time
            if event_type in ["sabc_tournament", "other_tournament"]
            else None,
            "weigh_in_time": weigh_in_time
            if event_type in ["sabc_tournament", "other_tournament"]
            else None,
            "lake_name": lake_name if lake_name else None,
            "ramp_name": ramp_name if ramp_name else None,
            "entry_fee": entry_fee if event_type == "sabc_tournament" else 0.00,
            "fish_limit": fish_limit if event_type == "sabc_tournament" else None,
            "holiday_name": name if event_type == "holiday" else None,
        }

        db(
            """
            UPDATE events
            SET date = :date, year = :year, name = :name, event_type = :event_type,
                description = :description, start_time = :start_time, weigh_in_time = :weigh_in_time,
                lake_name = :lake_name, ramp_name = :ramp_name, entry_fee = :entry_fee,
                fish_limit = :fish_limit, holiday_name = :holiday_name
            WHERE id = :event_id
        """,
            params,
        )

        # Handle poll closes date update if provided
        if poll_closes_date and event_type == "sabc_tournament":
            try:
                poll_closes_dt = datetime.fromisoformat(poll_closes_date)
                db(
                    "UPDATE polls SET closes_at = :closes_at WHERE event_id = :event_id",
                    {"closes_at": poll_closes_dt.isoformat(), "event_id": event_id},
                )
            except ValueError:
                pass  # Invalid datetime format, skip poll update

        return RedirectResponse("/admin/events?success=Event updated successfully", status_code=302)

    except Exception as e:
        error_msg = str(e)

        # Handle common database constraint errors with user-friendly messages
        if "UNIQUE constraint failed: events.date" in error_msg:
            error_msg = f"An event already exists on {date}. Please choose a different date."
        elif "NOT NULL constraint failed" in error_msg:
            error_msg = "Required field missing. Please fill in all required fields."
        elif "FOREIGN KEY constraint failed" in error_msg:
            error_msg = "Invalid lake or ramp selection. Please refresh the page and try again."
        else:
            error_msg = f"Failed to update event. Details: {error_msg}"

        return RedirectResponse(f"/admin/events?error={error_msg}", status_code=302)


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
                   e.entry_fee, e.fish_limit, e.holiday_name,
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
                    "fish_limit": event[10],
                    "holiday_name": event[11] or "",
                    "poll_closes_at": event[12],
                    "poll_starts_at": event[13],
                    "poll_id": event[14],
                    "poll_closed": bool(event[15]) if event[15] is not None else None,
                    "tournament_id": event[16],
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
            data.get("lake_name", ""),
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


def process_closed_polls():
    """Process closed polls and create tournaments from winning options."""
    try:
        # Find polls that are closed but haven't created tournaments yet
        closed_polls = db("""
            SELECT p.id, p.event_id, p.poll_type, p.closes_at
            FROM polls p
            JOIN events e ON p.event_id = e.id
            WHERE p.closed = 0
            AND datetime('now') > datetime(p.closes_at)
            AND p.poll_type = 'tournament_location'
            AND NOT EXISTS (SELECT 1 FROM tournaments t WHERE t.event_id = p.event_id)
            AND e.event_type = 'sabc_tournament'
        """)

        for poll_id, event_id, poll_type, closes_at in closed_polls:
            # Mark poll as closed
            db("UPDATE polls SET closed = 1 WHERE id = :poll_id", {"poll_id": poll_id})

            # Find the winning option (most votes)
            winning_option = db("""
                SELECT po.id, po.option_text, po.option_data
                FROM poll_options po
                WHERE po.poll_id = :poll_id
                AND (SELECT COUNT(*) FROM poll_votes pv WHERE pv.option_id = po.id) = (
                    SELECT MAX(vote_count) FROM (
                        SELECT COUNT(*) as vote_count
                        FROM poll_votes pv2
                        JOIN poll_options po2 ON pv2.option_id = po2.id
                        WHERE po2.poll_id = :poll_id
                        GROUP BY po2.id
                    )
                )
                ORDER BY po.id
                LIMIT 1
            """, {"poll_id": poll_id})

            if not winning_option:
                print(f"No winning option found for poll {poll_id}")
                continue

            option_id, option_text, option_data_str = winning_option[0]

            # Update poll with winning option
            db("UPDATE polls SET winning_option_id = :option_id WHERE id = :poll_id",
               {"option_id": option_id, "poll_id": poll_id})

            if poll_type == 'tournament_location':
                try:
                    option_data = json.loads(option_data_str) if option_data_str else {}

                    # Get event details
                    event_details = db("""
                        SELECT e.name, e.date, e.entry_fee, e.fish_limit, e.start_time, e.weigh_in_time
                        FROM events e WHERE e.id = :event_id
                    """, {"event_id": event_id})

                    if not event_details:
                        print(f"Event {event_id} not found")
                        continue

                    event_name, event_date, entry_fee, fish_limit, start_time, weigh_in_time = event_details[0]

                    # Extract lake and ramp info from winning option
                    lake_id = option_data.get('lake_id')
                    ramp_id = option_data.get('ramp_id')
                    tournament_start_time = option_data.get('start_time', start_time or '06:00')
                    tournament_end_time = option_data.get('end_time', weigh_in_time or '15:00')

                    # Find lake name from option text or use lake_id
                    lake_name = ""
                    ramp_name = ""
                    if option_text and " - " in option_text:
                        parts = option_text.split(" - ")
                        lake_name = parts[0].strip()
                        ramp_part = parts[1].split(" (")[0].strip()
                        ramp_name = ramp_part

                    # Create the tournament
                    tournament_id = db("""
                        INSERT INTO tournaments (
                            event_id, poll_id, name, lake_id, ramp_id, lake_name, ramp_name,
                            entry_fee, fish_limit, start_time, end_time,
                            complete, is_team, is_paper
                        )
                        VALUES (
                            :event_id, :poll_id, :name, :lake_id, :ramp_id, :lake_name, :ramp_name,
                            :entry_fee, :fish_limit, :start_time, :end_time,
                            0, 1, 0
                        )
                    """, {
                        "event_id": event_id,
                        "poll_id": poll_id,
                        "name": event_name,
                        "lake_id": lake_id,
                        "ramp_id": ramp_id,
                        "lake_name": lake_name,
                        "ramp_name": ramp_name,
                        "entry_fee": entry_fee or 25.0,
                        "fish_limit": fish_limit or 5,
                        "start_time": tournament_start_time,
                        "end_time": tournament_end_time
                    })

                    print(f"Created tournament {tournament_id} for event {event_id} from poll {poll_id}")

                except (json.JSONDecodeError, KeyError) as e:
                    print(f"Error processing poll option data for poll {poll_id}: {e}")
                    continue

        return len(closed_polls)

    except Exception as e:
        print(f"Error processing closed polls: {e}")
        return 0


