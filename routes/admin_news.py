"""Admin news management router module."""

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.auth_helpers import u
from core.database import db
from core.template_config import templates

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request):
    """Admin page for managing news announcements."""
    if not (user := u(request)) or not user.get("is_admin"):
        return RedirectResponse("/login")

    # Get all news items with last editor or original author
    news_items = db("""
        SELECT n.id, n.title, n.content, n.created_at, n.published, n.priority,
               n.expires_at, n.updated_at,
               COALESCE(e.name, a.name) as display_author_name,
               a.name as original_author_name,
               e.name as editor_name
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
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
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
            UPDATE news
            SET title = :title, content = :content, published = :published,
                priority = :priority, updated_at = CURRENT_TIMESTAMP,
                last_edited_by = :editor_id
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
