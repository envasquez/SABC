from typing import Any, Dict

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, get_admin_anglers_list, templates

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    news_items = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.published, n.priority,
               n.expires_at, COALESCE(e.name, a.name) as author_name
        FROM news n
        LEFT JOIN anglers a ON n.author_id = a.id
        LEFT JOIN anglers e ON n.last_edited_by = e.id
        ORDER BY n.created_at DESC
    """)

    return templates.TemplateResponse(
        "admin/news.html", {"request": request, "user": user, "news_items": news_items}
    )


@router.post("/admin/news/create")
async def create_news(
    request: Request, title: str = Form(...), content: str = Form(...), priority: int = Form(0)
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """
            INSERT INTO news (title, content, author_id, published, priority)
            VALUES (:title, :content, :author_id, :published, :priority)
        """,
            {
                "title": title.strip(),
                "content": content.strip(),
                "author_id": user["id"],
                "published": True,
                "priority": priority,
            },
        )
        return RedirectResponse("/admin/news?success=News created successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/news", str(e))


@router.post("/admin/news/{news_id}/update")
async def update_news(
    request: Request,
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db(
            """
            UPDATE news SET title = :title, content = :content, published = :published,
                priority = :priority, updated_at = CURRENT_TIMESTAMP, last_edited_by = :editor_id
            WHERE id = :id
        """,
            {
                "id": news_id,
                "title": title.strip(),
                "content": content.strip(),
                "published": True,
                "priority": priority,
                "editor_id": user["id"],
            },
        )
        return RedirectResponse("/admin/news?success=News updated successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/news", str(e))


@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    try:
        db("DELETE FROM news WHERE id = :id", {"id": news_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/admin/{page}")
async def admin_page(request: Request, page: str, upcoming_page: int = 1, past_page: int = 1):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    ctx: Dict[str, Any] = {"request": request, "user": user}

    if page == "events":
        per_page = 20
        upcoming_offset = (upcoming_page - 1) * per_page
        past_offset = (past_page - 1) * per_page

        # Get counts and events with pagination
        total_upcoming = db("SELECT COUNT(*) FROM events WHERE date >= CURRENT_DATE")[0][0]
        total_past = db(
            "SELECT COUNT(*) FROM events WHERE date < CURRENT_DATE AND event_type != 'holiday'"
        )[0][0]

        events = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type,
                   EXTRACT(DOW FROM e.date) as day_num,
                   CASE EXTRACT(DOW FROM e.date)
                       WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
                       WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
                       WHEN 6 THEN 'Saturday'
                   END as day_name,
                   EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
                   EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
                   EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id AND CURRENT_TIMESTAMP BETWEEN p.starts_at AND p.closes_at) as poll_active,
                   e.start_time, e.weigh_in_time, e.entry_fee, e.lake_name, e.ramp_name, e.holiday_name,
                   EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id AND t.complete = true) as tournament_complete
            FROM events e WHERE e.date >= CURRENT_DATE ORDER BY e.date LIMIT :limit OFFSET :offset
        """,
            {"limit": per_page, "offset": upcoming_offset},
        )

        ctx["events"] = [
            {
                "id": e[0],
                "date": e[1],
                "name": e[2] or "",
                "description": e[3] or "",
                "event_type": e[4] or "sabc_tournament",
                "day_name": e[6],
                "has_poll": bool(e[7]),
                "has_tournament": bool(e[8]),
                "poll_active": bool(e[9]),
                "start_time": e[10],
                "weigh_in_time": e[11],
                "entry_fee": e[12],
                "lake_name": e[13],
                "ramp_name": e[14],
                "holiday_name": e[15],
                "tournament_complete": bool(e[16]),
            }
            for e in events
        ]

        # Get past events for Past Events tab
        past_events_raw = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type, e.entry_fee,
                   e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
                   EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
                   EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
                   EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id AND t.complete = true) as tournament_complete,
                   EXISTS(SELECT 1 FROM tournaments t JOIN results r ON t.id = r.tournament_id WHERE t.event_id = e.id) as has_results
            FROM events e
            WHERE e.date < CURRENT_DATE AND e.event_type != 'holiday'
            ORDER BY e.date DESC
            LIMIT :limit OFFSET :offset
        """,
            {"limit": per_page, "offset": past_offset},
        )

        ctx["past_events"] = [
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
            for e in past_events_raw
        ]

        # Add pagination context
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
        ctx["users"] = get_admin_anglers_list()

    elif page == "tournaments":
        # Get all tournaments with event and result data
        tournaments = db("""
            SELECT t.id, t.event_id, e.date, e.name, t.lake_name, t.ramp_name,
                   t.entry_fee, t.complete, t.fish_limit,
                   COUNT(DISTINCT r.id) as result_count,
                   COUNT(DISTINCT tr.id) as team_result_count
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON t.id = r.tournament_id
            LEFT JOIN team_results tr ON t.id = tr.tournament_id
            GROUP BY t.id, t.event_id, e.date, e.name, t.lake_name, t.ramp_name,
                     t.entry_fee, t.complete, t.fish_limit
            ORDER BY e.date DESC
        """)

        ctx["tournaments"] = [
            {
                "id": t[0],
                "event_id": t[1],
                "date": t[2],
                "name": t[3],
                "lake_name": t[4],
                "ramp_name": t[5],
                "entry_fee": t[6],
                "complete": bool(t[7]),
                "fish_limit": t[8],
                "result_count": t[9],
                "team_result_count": t[10],
                "total_participants": t[9] + t[10],
            }
            for t in tournaments
        ]

    return templates.TemplateResponse(f"admin/{page}.html", ctx)
