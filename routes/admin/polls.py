import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.db_schema import engine
from core.helpers.logging_config import get_logger
from core.helpers.response import error_redirect
from core.query_service import QueryService
from routes.dependencies import admin, db, find_lake_by_id, get_all_ramps, get_lakes_list, templates

router = APIRouter()
logger = get_logger("admin.polls")


@router.get("/admin/polls/create")
async def create_poll_form(request: Request, event_id: int = Query(None)):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    try:
        if event_id is None:
            available_events = db("""
                SELECT e.id, e.date, e.name, e.event_type, e.description
                FROM events e LEFT JOIN polls p ON e.id = p.event_id
                WHERE p.id IS NULL AND e.date >= CURRENT_DATE AND e.event_type = 'sabc_tournament'
                ORDER BY e.date ASC
            """)
            return templates.TemplateResponse(
                "admin/new_poll.html",
                {"request": request, "user": user, "available_events": available_events},
            )

        event_data = db(
            "SELECT id, date, name, event_type, description FROM events WHERE id = :event_id",
            {"event_id": event_id},
        )
        if not event_data:
            return error_redirect("/admin/events", "Event not found")

        event = event_data[0]
        existing_poll = db(
            "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
        )
        if existing_poll:
            return RedirectResponse(
                f"/admin/polls/{existing_poll[0][0]}/edit?info=Poll already exists for this event",
                status_code=302,
            )
        events = db(
            "SELECT id, date, name, event_type, description FROM events WHERE (date >= CURRENT_DATE OR id = :event_id) AND event_type = 'sabc_tournament' ORDER BY date",
            {"event_id": event_id},
        )
        lakes = get_lakes_list()
        ramps = get_all_ramps()
        context = {
            "request": request,
            "user": user,
            "events": events,
            "selected_event": event,
            "lakes": lakes,
            "ramps": ramps,
        }
        return templates.TemplateResponse("admin/create_poll.html", context)
    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to load poll creation form: {str(e)}", status_code=302
        )


@router.get("/admin/polls/create/generic")
async def create_generic_poll_form(request: Request):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    return templates.TemplateResponse(
        "admin/create_generic_poll.html", {"request": request, "user": user}
    )


@router.post("/admin/polls/create")
async def create_poll(request: Request):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    try:
        form = await request.form()
        event_id_raw = form.get("event_id")
        event_id = int(event_id_raw) if event_id_raw and isinstance(event_id_raw, str) else None
        poll_type = form.get("poll_type", "")
        title = form.get("title", "")
        description = form.get("description", "")
        closes_at = form.get("closes_at", "")
        starts_at = form.get("starts_at", "")
        if poll_type == "tournament_location" and event_id:
            event_data = db(
                "SELECT id, name, event_type, date FROM events WHERE id = :event_id",
                {"event_id": event_id},
            )
            if not event_data:
                return error_redirect("/admin/events", "Event not found")

            event = event_data[0]
            existing_poll = db(
                "SELECT id FROM polls WHERE event_id = :event_id", {"event_id": event_id}
            )
            if existing_poll:
                return RedirectResponse(
                    f"/admin/polls/{existing_poll[0][0]}/edit?error=Poll already exists for this event",
                    status_code=302,
                )
        else:
            event = None
        if not title and poll_type == "tournament_location" and event:
            title = f"{event[1]} Lake Selection Poll"
        elif not title and event:
            title = f"Poll for {event[1]}"
        elif not title:
            title = "Generic Poll"
        if not starts_at:
            if event:
                event_date = datetime.strptime(event[3], "%Y-%m-%d")
                starts_at = (event_date - timedelta(days=7)).isoformat()
            else:
                starts_at = (datetime.now() + timedelta(days=1)).isoformat()

        poll_id = db(
            """
            INSERT INTO polls (title, description, poll_type, event_id, created_by,
                             starts_at, closes_at, closed, multiple_votes)
            VALUES (:title, :description, :poll_type, :event_id, :created_by,
                   :starts_at, :closes_at, 0, 0)
        """,
            {
                "title": title,
                "description": description
                if description
                else (
                    f"Vote for location for {event[1]}"
                    if event
                    else "Vote for your preferred option"
                ),
                "poll_type": poll_type,
                "event_id": event_id if event_id else None,
                "created_by": user["id"],
                "starts_at": starts_at,
                "closes_at": closes_at,
            },
        )
        if poll_type == "tournament_location":
            selected_lake_ids = form.getlist("lake_ids")
            if selected_lake_ids:
                for lake_id_raw in selected_lake_ids:
                    if isinstance(lake_id_raw, str):
                        lake_name = find_lake_by_id(int(lake_id_raw), "name")
                        if lake_name:
                            db(
                                """
                                INSERT INTO poll_options (poll_id, option_text, option_data)
                                VALUES (:poll_id, :option_text, :option_data)
                            """,
                                {
                                    "poll_id": poll_id,
                                    "option_text": lake_name,
                                    "option_data": json.dumps({"lake_id": int(lake_id_raw)}),
                                },
                            )
            else:
                all_lakes = get_lakes_list()
                for lake in all_lakes:
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": lake["display_name"],
                            "option_data": json.dumps({"lake_id": lake["id"]}),
                        },
                    )
        elif poll_type == "generic":
            poll_options = form.getlist("poll_options[]")
            for option_text_raw in poll_options:
                if isinstance(option_text_raw, str) and option_text_raw.strip():
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": option_text_raw.strip(),
                            "option_data": json.dumps({}),
                        },
                    )
        else:
            for key in form.keys():
                value = form[key]
                if key.startswith("option_") and isinstance(value, str) and value.strip():
                    db(
                        """
                        INSERT INTO poll_options (poll_id, option_text, option_data)
                        VALUES (:poll_id, :option_text, :option_data)
                    """,
                        {
                            "poll_id": poll_id,
                            "option_text": value.strip(),
                            "option_data": json.dumps({}),
                        },
                    )
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll created successfully", status_code=302
        )
    except Exception as e:
        logger.error(
            "Error creating poll",
            extra={
                "admin_user_id": user.get("id"),
                "event_id": event_id if "event_id" in locals() else None,
                "poll_type": poll_type if "poll_type" in locals() else None,
                "error": str(e),
            },
            exc_info=True,
        )
        return RedirectResponse(
            f"/admin/events?error=Failed to create poll: {str(e)}", status_code=302
        )


@router.get("/admin/polls/{poll_id}/edit")
async def edit_poll_form(request: Request, poll_id: int):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    try:
        poll_data = db(
            "SELECT p.id, p.title, p.closes_at, p.poll_type, p.starts_at, p.description FROM polls p WHERE p.id = :poll_id",
            {"poll_id": poll_id},
        )
        if not poll_data:
            return error_redirect("/polls", "Poll not found")

        poll = poll_data[0]
        context = {"request": request, "user": user, "poll": poll}
        with engine.connect() as conn:
            qs = QueryService(conn)
            context["poll_options"] = qs.get_poll_options_with_votes(poll_id, include_details=True)
        if poll[3] == "tournament_location":  # poll_type
            lakes = get_lakes_list()
            context["lakes"] = lakes
            selected_lakes = db(
                """
                SELECT DISTINCT (option_data->>'lake_id')::int as lake_id
                FROM poll_options WHERE poll_id = :poll_id
                AND option_data->>'lake_id' IS NOT NULL
            """,
                {"poll_id": poll_id},
            )
            selected_lake_ids = set()
            for lake_row in selected_lakes:
                if lake_row[0] is not None:
                    selected_lake_ids.add(int(lake_row[0]))
            context["selected_lake_ids"] = selected_lake_ids
            return templates.TemplateResponse("admin/edit_tournament_poll.html", context)
        else:
            return templates.TemplateResponse("admin/edit_poll.html", context)
    except Exception as e:
        return RedirectResponse(f"/polls?error=Failed to load poll: {str(e)}", status_code=302)


@router.post("/admin/polls/{poll_id}/edit")
async def update_poll(request: Request, poll_id: int):
    if isinstance(user := admin(request), RedirectResponse):
        return user
    try:
        form = await request.form()
        title = form.get("title", "").strip()
        description = form.get("description", "").strip()
        starts_at = form.get("starts_at", "")
        closes_at = form.get("closes_at", "")
        poll_options = form.getlist("poll_options[]")
        option_ids = form.getlist("option_ids[]")
        if not title:
            return RedirectResponse(
                f"/admin/polls/{poll_id}/edit?error=Title is required", status_code=302
            )
        db(
            """
            UPDATE polls
            SET title = :title, description = :description, starts_at = :starts_at, closes_at = :closes_at
            WHERE id = :poll_id
        """,
            {
                "title": title,
                "description": description,
                "starts_at": starts_at if starts_at else None,
                "closes_at": closes_at if closes_at else None,
                "poll_id": poll_id,
            },
        )
        for i, option_text in enumerate(poll_options):
            option_text = option_text.strip()
            if not option_text:
                continue

            option_id = option_ids[i] if i < len(option_ids) and option_ids[i] else None
            if option_id:
                db(
                    """
                    UPDATE poll_options
                    SET option_text = :option_text
                    WHERE id = :option_id AND poll_id = :poll_id
                """,
                    {"option_text": option_text, "option_id": option_id, "poll_id": poll_id},
                )
            else:
                db(
                    """
                    INSERT INTO poll_options (poll_id, option_text, option_data)
                    VALUES (:poll_id, :option_text, :option_data)
                """,
                    {"poll_id": poll_id, "option_text": option_text, "option_data": "{}"},
                )
        logger.info(
            "Poll updated successfully",
            extra={
                "admin_user_id": user.get("id"),
                "poll_id": poll_id,
                "title": title,
            },
        )
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?success=Poll updated successfully", status_code=302
        )
    except Exception as e:
        logger.error(
            "Error updating poll",
            extra={
                "admin_user_id": user.get("id"),
                "poll_id": poll_id,
                "error": str(e),
            },
            exc_info=True,
        )
        return RedirectResponse(
            f"/admin/polls/{poll_id}/edit?error=Failed to update poll: {str(e)}", status_code=302
        )


@router.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int):
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        db("DELETE FROM poll_votes WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM poll_options WHERE poll_id = :poll_id", {"poll_id": poll_id})
        db("DELETE FROM polls WHERE id = :poll_id", {"poll_id": poll_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/admin/votes/{vote_id}")
async def delete_vote(request: Request, vote_id: int):
    if isinstance(admin(request), RedirectResponse):
        return JSONResponse({"error": "Authentication required"}, status_code=401)
    try:
        vote_details = db(
            """
            SELECT pv.id, a.name as voter_name, po.option_text, p.title
            FROM poll_votes pv
            JOIN anglers a ON pv.angler_id = a.id
            JOIN poll_options po ON pv.option_id = po.id
            JOIN polls p ON pv.poll_id = p.id
            WHERE pv.id = :vote_id
        """,
            {"vote_id": vote_id},
        )
        if not vote_details:
            return JSONResponse({"error": "Vote not found"}, status_code=404)
        db("DELETE FROM poll_votes WHERE id = :vote_id", {"vote_id": vote_id})
        return JSONResponse(
            {
                "success": True,
                "message": f"Deleted vote by {vote_details[0][1]} for '{vote_details[0][2]}' in poll '{vote_details[0][3]}'",
            },
            status_code=200,
        )
    except Exception as e:
        return JSONResponse({"error": f"Failed to delete vote: {str(e)}"}, status_code=500)
