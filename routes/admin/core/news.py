from typing import List

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.db_schema import Angler, News, get_session, utc_now
from core.email import send_news_notification
from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect, sanitize_error_message
from routes.dependencies import templates

logger = get_logger(__name__)

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request):
    user = require_admin(request)

    with get_session() as session:
        news_query = (
            session.query(
                News.id,
                News.title,
                News.content,
                News.created_at,
                News.published,
                News.priority,
                News.updated_at,
                Angler.name.label("author_name"),
            )
            .outerjoin(Angler, News.author_id == Angler.id)
            .order_by(News.priority.desc(), News.created_at.desc())
        )
        news_items = news_query.all()

    return templates.TemplateResponse(
        "admin/news.html", {"request": request, "user": user, "news_items": news_items}
    )


@router.post("/admin/news/create")
async def create_news(
    request: Request, title: str = Form(...), content: str = Form(...), priority: int = Form(0)
):
    user = require_admin(request)
    try:
        # Create the news post
        with get_session() as session:
            news_item = News(
                title=title.strip(),
                content=content.strip(),
                author_id=user["id"],
                published=True,
                priority=priority,
            )
            session.add(news_item)
            # Context manager will commit automatically on successful exit

        # Send email notifications to all members (non-blocking)
        try:
            with get_session() as session:
                # Get all member emails (members only, exclude null emails)
                member_emails: List[str] = [
                    email
                    for (email,) in session.query(Angler.email)
                    .filter(Angler.member == True, Angler.email.isnot(None))  # noqa: E712
                    .all()
                    if email
                ]

            if member_emails:
                send_news_notification(member_emails, title.strip(), content.strip())
            else:
                logger.info("No member emails found - skipping news notification")

        except Exception as email_error:
            # Log email failure but don't fail the news post creation
            logger.error(f"Failed to send news notifications: {email_error}")

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
    try:
        with get_session() as session:
            news_item = session.query(News).filter(News.id == news_id).first()
            if news_item:
                news_item.title = title.strip()
                news_item.content = content.strip()
                news_item.published = True
                news_item.priority = priority
                news_item.last_edited_by = user["id"]  # type: ignore[assignment]
                news_item.updated_at = utc_now()
                # Context manager will commit automatically on successful exit

        return RedirectResponse("/admin/news?success=News updated successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/news", str(e))


@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int):
    _user = require_admin(request)
    try:
        with get_session() as session:
            news_item = session.query(News).filter(News.id == news_id).first()
            if news_item:
                session.delete(news_item)
                # Context manager will commit automatically on successful exit

        return JSONResponse({"success": True})
    except Exception as e:
        return JSONResponse(
            {"error": sanitize_error_message(e, "Operation failed")}, status_code=500
        )
