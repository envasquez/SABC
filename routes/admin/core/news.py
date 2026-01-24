from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Form, HTTPException, Request, Response
from fastapi.responses import RedirectResponse

from core.db_schema import Angler, News, get_session, utc_now
from core.email import send_news_notification
from core.helpers.auth import require_admin
from core.helpers.crud import delete_entity
from core.helpers.logging import get_logger
from core.helpers.response import error_redirect
from core.helpers.sanitize import sanitize_html
from routes.dependencies import templates

logger = get_logger(__name__)

router = APIRouter()


@router.get("/admin/news")
async def admin_news(request: Request, show_archived: bool = False):
    user = require_admin(request)

    with get_session() as session:
        news_query = session.query(
            News.id,
            News.title,
            News.content,
            News.created_at,
            News.published,
            News.priority,
            News.updated_at,
            Angler.name.label("author_name"),
            News.archived,
            News.expires_at,
        ).outerjoin(Angler, News.author_id == Angler.id)

        # Filter based on archived status
        if show_archived:
            news_query = news_query.filter(News.archived.is_(True))
        else:
            news_query = news_query.filter(News.archived.isnot(True))

        news_query = news_query.order_by(News.priority.desc(), News.created_at.desc())
        news_items = news_query.all()

    return templates.TemplateResponse(
        "admin/news.html",
        {
            "request": request,
            "user": user,
            "news_items": news_items,
            "show_archived": show_archived,
        },
    )


@router.post("/admin/news/create")
async def create_news(
    request: Request,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
    auto_archive_at: Optional[str] = Form(default=None),
):
    user = require_admin(request)

    # Validate inputs
    title_clean = title.strip()
    content_clean = content.strip()

    if not title_clean:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    if not content_clean:
        raise HTTPException(status_code=422, detail="Content cannot be empty")

    # Sanitize inputs to prevent XSS
    title_safe = sanitize_html(title_clean)
    content_safe = sanitize_html(content_clean)

    # Parse auto_archive_at date or default to 30 days from now
    expires_at: Optional[datetime] = None
    if auto_archive_at and auto_archive_at.strip():
        try:
            # Parse date string (YYYY-MM-DD) and set to end of day
            parsed_date = datetime.strptime(auto_archive_at.strip(), "%Y-%m-%d")
            expires_at = parsed_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            pass  # Invalid date format, use default
    if expires_at is None:
        # Default to 30 days from now
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        expires_at = expires_at.replace(hour=23, minute=59, second=59)

    try:
        # Create the news post
        with get_session() as session:
            news_item = News(
                title=title_safe,
                content=content_safe,
                author_id=user["id"],
                published=True,
                priority=priority,
                expires_at=expires_at,
            )
            session.add(news_item)
            # Context manager will commit automatically on successful exit

        # Send email notifications to all members (non-blocking)
        try:
            with get_session() as session:
                # Get all member emails (members only, exclude null emails and system admin)
                member_emails: List[str] = [
                    email
                    for (email,) in session.query(Angler.email)
                    .filter(Angler.member == True, Angler.email.isnot(None))  # noqa: E712
                    .all()
                    if email and email.lower() != "admin@sabc.com"
                ]

            if member_emails:
                author = user.get("name")
                send_news_notification(
                    member_emails,
                    title_safe,
                    content_safe,
                    author_name=str(author) if author else None,
                )
            else:
                logger.info("No member emails found - skipping news notification")

        except Exception as email_error:
            # Log email failure but don't fail the news post creation
            logger.error(f"Failed to send news notifications: {email_error}")

        return RedirectResponse("/admin/news?success=News created successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/news", str(e))


@router.get("/admin/news/{news_id}/edit")
async def edit_news_form(request: Request, news_id: int):
    """GET endpoint for editing news - returns the edit form."""
    user = require_admin(request)

    with get_session() as session:
        news_item = session.query(News).filter(News.id == news_id).first()
        if not news_item:
            return RedirectResponse(
                f"/admin/news?error=News item with ID {news_id} not found", status_code=302
            )

    # Return the admin news page with the news item data
    return templates.TemplateResponse(
        "admin/news.html",
        {
            "request": request,
            "user": user,
            "edit_news": news_item,
        },
    )


@router.post("/admin/news/{news_id}/update")
async def update_news(
    request: Request,
    news_id: int,
    title: str = Form(...),
    content: str = Form(...),
    priority: int = Form(0),
    auto_archive_at: Optional[str] = Form(default=None),
):
    user = require_admin(request)

    # Validate inputs
    title_clean = title.strip()
    content_clean = content.strip()

    if not title_clean:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    if not content_clean:
        raise HTTPException(status_code=422, detail="Content cannot be empty")

    # Sanitize inputs to prevent XSS
    title_safe = sanitize_html(title_clean)
    content_safe = sanitize_html(content_clean)

    # Parse auto_archive_at date
    expires_at: Optional[datetime] = None
    if auto_archive_at and auto_archive_at.strip():
        try:
            # Parse date string (YYYY-MM-DD) and set to end of day
            parsed_date = datetime.strptime(auto_archive_at.strip(), "%Y-%m-%d")
            expires_at = parsed_date.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        except ValueError:
            pass  # Invalid date format, keep existing value

    try:
        with get_session() as session:
            news_item = session.query(News).filter(News.id == news_id).first()
            if news_item:
                news_item.title = title_safe
                news_item.content = content_safe
                news_item.published = True
                news_item.priority = priority
                news_item.last_edited_by = user["id"]  # type: ignore[assignment]
                news_item.updated_at = utc_now()
                if expires_at is not None:
                    news_item.expires_at = expires_at
                # Context manager will commit automatically on successful exit

        return RedirectResponse("/admin/news?success=News updated successfully", status_code=302)
    except Exception as e:
        return error_redirect("/admin/news", str(e))


@router.post("/admin/news/test-email")
async def test_news_email(request: Request, title: str = Form(...), content: str = Form(...)):
    """Send a test email notification to the currently logged-in admin."""
    user = require_admin(request)

    # Get admin's email
    admin_email = user.get("email")
    if not admin_email or not isinstance(admin_email, str):
        return error_redirect("/admin/news", "Your admin account has no email address configured")

    try:
        # Send test email only to the admin
        author = user.get("name")
        success = send_news_notification(
            [admin_email],
            title.strip(),
            content.strip(),
            author_name=str(author) if author else None,
        )

        if success:
            return RedirectResponse(
                f"/admin/news?success=Test email sent to {admin_email}", status_code=302
            )
        else:
            return error_redirect(
                "/admin/news", "Failed to send test email. Check SMTP configuration."
            )

    except Exception as e:
        logger.error(f"Test email error: {e}")
        return error_redirect("/admin/news", "Failed to send test email")


@router.post("/admin/news/{news_id}/delete")
async def delete_news_post(request: Request, news_id: int) -> Response:
    """POST endpoint for deleting news (for form submissions)."""
    return delete_entity(
        request,
        news_id,
        News,
        redirect_url="/admin/news",
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )


@router.delete("/admin/news/{news_id}")
async def delete_news(request: Request, news_id: int) -> Response:
    """DELETE endpoint for deleting news (for AJAX requests)."""
    return delete_entity(
        request,
        news_id,
        News,
        success_message="News deleted successfully",
        error_message="Failed to delete news",
    )


@router.post("/admin/news/{news_id}/archive")
async def archive_news(request: Request, news_id: int) -> RedirectResponse:
    """Archive a news item (soft delete)."""
    require_admin(request)

    try:
        with get_session() as session:
            news_item = session.query(News).filter(News.id == news_id).first()
            if news_item:
                news_item.archived = True
                news_item.updated_at = utc_now()

        return RedirectResponse("/admin/news?success=News archived successfully", status_code=302)
    except Exception as e:
        logger.error(f"Failed to archive news: {e}")
        return error_redirect("/admin/news", "Failed to archive news")


@router.post("/admin/news/{news_id}/unarchive")
async def unarchive_news(request: Request, news_id: int) -> RedirectResponse:
    """Unarchive a news item (restore from archive)."""
    require_admin(request)

    try:
        with get_session() as session:
            news_item = session.query(News).filter(News.id == news_id).first()
            if news_item:
                news_item.archived = False
                news_item.updated_at = utc_now()

        return RedirectResponse(
            "/admin/news?show_archived=true&success=News restored successfully",
            status_code=302,
        )
    except Exception as e:
        logger.error(f"Failed to unarchive news: {e}")
        return error_redirect("/admin/news?show_archived=true", "Failed to restore news")
