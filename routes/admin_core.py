"""Admin core routes - news management and dashboard."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from routes.dependencies import admin, db, templates, u

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request):
    """Admin page for managing news announcements."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

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
    """Create a new news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

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
        return RedirectResponse(f"/admin/news?error={str(e)}", status_code=302)


@router.post("/admin/news/{news_id}/update")
async def update_news(
    request: Request,
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
):
    """Update an existing news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

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
        return RedirectResponse(f"/admin/news?error={str(e)}", status_code=302)


@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int):
    """Delete a news announcement."""
    if not (user := u(request)) or not user.get("is_admin"):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    try:
        db("DELETE FROM news WHERE id = :id", {"id": news_id})
        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/admin/{page}")
async def admin_page(request: Request, page: str, upcoming_page: int = 1, past_page: int = 1):
    """Admin dashboard pages (events and users)."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    ctx = {"request": request, "user": user}

    if page == "events":
        per_page = 20
        upcoming_offset = (upcoming_page - 1) * per_page
        (past_page - 1) * per_page

        # Get counts and events with pagination
        total_upcoming = db("SELECT COUNT(*) FROM events WHERE date >= date('now')")[0][0]
        db("SELECT COUNT(*) FROM events WHERE date < date('now')")[0][0]

        events = db(
            """
            SELECT e.id, e.date, e.name, e.description, e.event_type,
                   strftime('%w', e.date) as day_num,
                   CASE strftime('%w', e.date)
                       WHEN '0' THEN 'Sunday' WHEN '1' THEN 'Monday' WHEN '2' THEN 'Tuesday'
                       WHEN '3' THEN 'Wednesday' WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
                       WHEN '6' THEN 'Saturday'
                   END as day_name,
                   EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
                   EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
                   e.start_time, e.weigh_in_time, e.lake_name, e.ramp_name, e.entry_fee, e.holiday_name
            FROM events e WHERE e.date >= date('now') ORDER BY e.date LIMIT :limit OFFSET :offset
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
                "start_time": e[9],
                "weigh_in_time": e[10],
                "lake_name": e[11],
                "ramp_name": e[12],
                "entry_fee": e[13],
                "holiday_name": e[14],
            }
            for e in events
        ]

        # Add pagination context
        ctx.update(
            {
                "upcoming_page": upcoming_page,
                "upcoming_total_pages": (total_upcoming + per_page - 1) // per_page,
                "upcoming_has_prev": upcoming_page > 1,
                "upcoming_has_next": upcoming_page < (total_upcoming + per_page - 1) // per_page,
                "total_upcoming": total_upcoming,
                "per_page": per_page,
            }
        )

    elif page == "users":
        tab = request.query_params.get("tab", "active")
        ctx["users"] = db(
            "SELECT id, name, email, member, is_admin, active FROM anglers WHERE "
            + ("member = 1 AND active = 0" if tab == "inactive" else "active = 1")
            + " ORDER BY "
            + ("name" if tab == "inactive" else "is_admin DESC, member DESC, name")
        )
        ctx["current_tab"] = tab

    return templates.TemplateResponse(f"admin/{page}.html", ctx)
