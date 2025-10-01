from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.helpers.auth import require_admin
from core.helpers.response import error_redirect
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request):
    user = require_admin(request)

    if isinstance(user, RedirectResponse):
        return user

    news_items = db(
        """SELECT n.id, n.title, n.content, n.created_at, n.published, n.priority, n.updated_at, a.name as author_name
           FROM news n
           LEFT JOIN anglers a ON n.author_id = a.id
           ORDER BY n.priority DESC, n.created_at DESC"""
    )

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
            """INSERT INTO news (title, content, author_id, published, priority)
               VALUES (:title, :content, :author_id, :published, :priority)""",
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
            """UPDATE news SET title = :title, content = :content, published = :published,
               priority = :priority, last_edited_by = :editor_id, updated_at = CURRENT_TIMESTAMP
               WHERE id = :id""",
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
