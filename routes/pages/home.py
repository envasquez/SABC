import os
import re
import time
from datetime import date
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import case, func
from sqlalchemy.orm import aliased

from core.db_schema import (
    Angler,
    Event,
    Lake,
    News,
    Poll,
    PollOption,
    PollVote,
    Ramp,
    Result,
    TeamResult,
    Tournament,
    engine,
    get_session,
)
from core.deps import templates
from core.email import send_contact_email
from core.helpers.auth import get_user_optional
from core.helpers.logging import get_logger
from core.helpers.pagination import PaginationState
from core.helpers.poll_day_info import get_poll_day_info
from core.helpers.response import error_redirect, success_redirect
from core.query_service import QueryService
from routes.dependencies import get_lakes_list, get_ramps_for_lake

router = APIRouter()


async def home_paginated(request: Request, page: int = 1):
    user = get_user_optional(request)
    items_per_page = 4

    with get_session() as session:
        # Get total COMPLETED SABC tournament count (for pagination)
        # Includes cancelled tournaments since they appear in the completed tab
        total_completed_tournaments = (
            session.query(func.count(Tournament.id))
            .join(Event, Tournament.event_id == Event.id)
            .filter((Tournament.complete.is_(True)) | (Event.is_cancelled.is_(True)))
            .filter(Event.event_type == "sabc_tournament")
            .scalar()
            or 0
        )

        pagination = PaginationState(
            page=page,
            items_per_page=items_per_page,
            total_items=total_completed_tournaments,
        )

        if pagination.is_out_of_range():
            return RedirectResponse(f"/?p={pagination.total_pages}", status_code=303)

        page = max(1, page)
        pagination = PaginationState(
            page=page,
            items_per_page=items_per_page,
            total_items=total_completed_tournaments,
        )
        offset = pagination.offset
        total_pages = pagination.total_pages

        # Base query for tournament data
        def build_tournament_query(complete_filter: bool | None = None):
            query = (
                session.query(
                    Tournament.id,
                    Event.date,
                    Event.name,
                    Event.description,
                    Lake.display_name.label("lake_display_name"),
                    Lake.yaml_key.label("lake_name"),
                    Ramp.name.label("ramp_name"),
                    Ramp.google_maps_iframe.label("ramp_google_maps"),
                    Lake.google_maps_iframe.label("lake_google_maps"),
                    Tournament.start_time,
                    Tournament.end_time,
                    Tournament.entry_fee,
                    Tournament.fish_limit,
                    Tournament.limit_type,
                    Tournament.is_team,
                    Tournament.is_paper,
                    Tournament.complete,
                    Tournament.poll_id,
                    func.count(func.distinct(Result.angler_id)).label("total_anglers"),
                    func.sum(Result.num_fish).label("total_fish"),
                    func.sum(Result.total_weight).label("total_weight"),
                    Tournament.aoy_points,
                    Event.event_type,
                    Event.is_cancelled,
                )
                .join(Event, Tournament.event_id == Event.id)
                .outerjoin(Lake, Tournament.lake_id == Lake.id)
                .outerjoin(Ramp, Tournament.ramp_id == Ramp.id)
                .outerjoin(
                    Result,
                    (Tournament.id == Result.tournament_id) & (Result.disqualified.is_(False)),
                )
                .outerjoin(
                    Angler,
                    (Result.angler_id == Angler.id) & (Angler.name != "Admin User"),
                )
                .group_by(
                    Tournament.id,
                    Event.date,
                    Event.name,
                    Event.description,
                    Lake.display_name,
                    Lake.yaml_key,
                    Ramp.name,
                    Ramp.google_maps_iframe,
                    Lake.google_maps_iframe,
                    Tournament.start_time,
                    Tournament.end_time,
                    Tournament.entry_fee,
                    Tournament.fish_limit,
                    Tournament.limit_type,
                    Tournament.is_team,
                    Tournament.is_paper,
                    Tournament.complete,
                    Tournament.poll_id,
                    Tournament.aoy_points,
                    Event.event_type,
                    Event.is_cancelled,
                )
            )
            if complete_filter is not None:
                query = query.filter(Tournament.complete.is_(complete_filter))
            return query

        # Get COMPLETED SABC tournaments with pagination (includes cancelled tournaments)
        completed_tournaments_query = (
            build_tournament_query()
            .filter(Event.event_type == "sabc_tournament")
            .filter((Tournament.complete.is_(True)) | (Event.is_cancelled.is_(True)))
            .order_by(Event.date.desc())
            .limit(items_per_page)
            .offset(offset)
            .all()
        )

        # Get ALL UPCOMING tournaments (no pagination), excludes cancelled ones
        upcoming_tournaments_query = (
            build_tournament_query(complete_filter=False)
            .filter(Event.is_cancelled.isnot(True))
            .order_by(Event.date.asc())
            .all()
        )

        # Count upcoming tournaments
        total_upcoming_tournaments = len(upcoming_tournaments_query)

        # Combine both queries
        tournaments_query = list(completed_tournaments_query) + list(upcoming_tournaments_query)

        tournaments_with_results: List[Dict[str, Any]] = []
        for tournament in tournaments_query:
            tournament_id = tournament[0]
            poll_id = tournament[17]

            # Get top 3 team results for this tournament
            Angler1 = aliased(Angler)
            Angler2 = aliased(Angler)
            top_results_query = (
                session.query(
                    TeamResult.place_finish,
                    Angler1.name.label("angler1_name"),
                    Angler2.name.label("angler2_name"),
                    TeamResult.total_weight,
                    case((TeamResult.angler2_id.is_(None), 1), else_=2).label("team_size"),
                )
                .join(Angler1, TeamResult.angler1_id == Angler1.id)
                .outerjoin(Angler2, TeamResult.angler2_id == Angler2.id)
                .filter(
                    TeamResult.tournament_id == tournament_id,
                    Angler1.name != "Admin User",
                    (Angler2.name != "Admin User") | (Angler2.name.is_(None)),
                )
                .order_by(TeamResult.place_finish.asc())
                .limit(3)
                .all()
            )

            # Get poll data and check if user has voted
            import json

            poll_data = None
            user_has_voted = False
            poll_is_open = False

            if poll_id:
                # Get poll status
                poll = session.query(Poll).filter(Poll.id == poll_id).first()
                if poll:
                    from core.helpers.timezone import now_local

                    now = now_local()
                    # Poll datetimes are already timezone-aware from database
                    if poll.starts_at and poll.closes_at:
                        poll_is_open = poll.starts_at <= now <= poll.closes_at

                # Get poll options with vote counts (for all users if they've voted)
                poll_options = (
                    session.query(
                        PollOption.id,
                        PollOption.option_text,
                        PollOption.option_data,
                        func.count(PollVote.id).label("vote_count"),
                    )
                    .outerjoin(PollVote, PollOption.id == PollVote.option_id)
                    .filter(PollOption.poll_id == poll_id)
                    .group_by(PollOption.id, PollOption.option_text, PollOption.option_data)
                    .all()
                )

                # Check if user has voted
                if user:
                    user_id = user.get("id") if isinstance(user, dict) else user.id  # type: ignore[attr-defined]
                    user_vote = (
                        session.query(PollVote)
                        .filter(PollVote.poll_id == poll_id, PollVote.angler_id == user_id)
                        .first()
                    )
                    user_has_voted = user_vote is not None

                # Show poll data if user has voted OR if poll is closed (results are public)
                if (user_has_voted or not poll_is_open) and poll_options:
                    poll_data = []
                    for opt in poll_options:
                        try:
                            option_data_dict = (
                                json.loads(opt.option_data) if opt.option_data else {}
                            )
                        except (json.JSONDecodeError, TypeError):
                            option_data_dict = {}

                        poll_data.append(
                            {
                                "option_text": opt.option_text,
                                "option_data": option_data_dict,
                                "vote_count": opt.vote_count,
                            }
                        )

            # Check if tournament date has passed (for display purposes)
            tournament_date = tournament[1]
            is_past = tournament_date < date.today() if tournament_date else False

            # Sunrise + forecast for upcoming, non-cancelled tournaments. Sunrise
            # is always available; weather is only populated within the NWS
            # forecast window (~7 days), otherwise the weather field is None.
            day_info: Any = None
            is_cancelled = tournament[23] or False
            if not is_past and not is_cancelled and tournament_date:
                try:
                    day_info = get_poll_day_info(tournament_date)
                except Exception as e:
                    logger.warning(f"day info lookup failed for tournament {tournament[0]}: {e}")

            tournament_dict = {
                "id": tournament[0],
                "date": tournament_date,
                "name": tournament[2],
                "description": tournament[3],
                "lake_display_name": tournament[4],
                "lake_name": tournament[5],
                "ramp_name": tournament[6],
                "ramp_google_maps": tournament[7],
                "lake_google_maps": tournament[8],
                "google_maps_iframe": tournament[7] or tournament[8],
                "start_time": tournament[9],
                "end_time": tournament[10],
                "entry_fee": tournament[11] or 50.0,
                "fish_limit": tournament[12] or 5,
                "limit_type": tournament[13] or "per_person",
                "is_team": tournament[14],
                "is_paper": tournament[15],
                "complete": tournament[16],
                "is_past": is_past,  # True if date has passed, regardless of complete status
                "poll_id": poll_id,
                "total_anglers": tournament[18] or 0,
                "total_fish": tournament[19] or 0,
                "total_weight": tournament[20] or 0.0,
                "aoy_points": tournament[21] if tournament[21] is not None else True,
                "event_type": tournament[22],
                "is_cancelled": is_cancelled,
                "day_info": day_info,
                "top_results": top_results_query,
                "poll_data": poll_data,
                "user_has_voted": user_has_voted,
                "poll_is_open": poll_is_open,
            }
            tournaments_with_results.append(tournament_dict)

        # Get member count (only members with current dues)
        member_count = (
            session.query(func.count(Angler.id))
            .filter(Angler.member.is_(True), Angler.dues_paid_through >= date.today())
            .scalar()
            or 0
        )

        # Get cancelled upcoming tournaments for alert banner
        cancelled_tournaments_query = (
            session.query(
                Event.id,
                Event.date,
                Event.name,
                Event.description,
                Lake.display_name.label("lake_name"),
            )
            .join(Tournament, Tournament.event_id == Event.id)
            .outerjoin(Lake, Tournament.lake_id == Lake.id)
            .filter(
                Event.is_cancelled.is_(True),
                Event.event_type == "sabc_tournament",
                Event.date >= date.today(),  # Only show upcoming cancelled tournaments
            )
            .order_by(Event.date.asc())
            .all()
        )
        cancelled_tournaments = [
            {
                "id": ct[0],
                "date": ct[1],
                "name": ct[2],
                "description": ct[3],
                "lake_name": ct[4],
            }
            for ct in cancelled_tournaments_query
        ]

        # Get latest news
        # Note: We exclude admin@sabc.com from author display (default admin user)
        Author = aliased(Angler)
        Editor = aliased(Angler)
        latest_news = (
            session.query(
                News.id,
                News.title,
                News.content,
                News.created_at,
                News.updated_at,
                News.priority,
                func.coalesce(Editor.name, Author.name).label("display_author_name"),
                case(
                    (Author.email == "admin@sabc.com", None),
                    else_=Author.name,
                ).label("original_author_name"),
                case(
                    (Editor.email == "admin@sabc.com", None),
                    else_=Editor.name,
                ).label("editor_name"),
            )
            .outerjoin(Author, News.author_id == Author.id)
            .outerjoin(Editor, News.last_edited_by == Editor.id)
            .filter(
                News.published.is_(True),
                News.archived.isnot(True),
                (News.expires_at.is_(None)) | (News.expires_at > func.current_timestamp()),
            )
            .order_by(News.priority.desc(), News.created_at.desc())
            .limit(5)
            .all()
        )

    # Pagination metadata (total_pages already calculated above)
    start_index = offset + 1
    end_index = min(offset + items_per_page, total_completed_tournaments)

    # Calculate page range for pagination (show up to 5 page numbers)
    max_pages_shown = 5
    half_range = max_pages_shown // 2

    if total_pages <= max_pages_shown:
        page_range = range(1, total_pages + 1)
    else:
        start_page = max(1, page - half_range)
        end_page = min(total_pages, page + half_range)

        # Adjust if we're near the start or end
        if end_page - start_page + 1 < max_pages_shown:
            if start_page == 1:
                end_page = min(total_pages, start_page + max_pages_shown - 1)
            else:
                start_page = max(1, end_page - max_pages_shown + 1)

        page_range = range(start_page, end_page + 1)

    # Get year navigation links
    with engine.connect() as conn:
        qs = QueryService(conn)
        year_links = qs.get_tournament_years_with_first_id(items_per_page)

    # Get lakes data for poll results rendering
    lakes_data = [
        {
            "id": lake["id"],
            "name": lake["display_name"],
            "ramps": [
                {"id": r["id"], "name": r["name"].title()} for r in get_ramps_for_lake(lake["id"])
            ],
        }
        for lake in get_lakes_list()
    ]

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "user": user,
            "all_tournaments": tournaments_with_results,
            "current_page": pagination.page,
            "total_pages": pagination.total_pages,
            "page_range": page_range,
            "has_prev": pagination.has_prev,
            "has_next": pagination.has_next,
            "start_index": start_index,
            "end_index": end_index,
            "total_tournaments": total_completed_tournaments,
            "total_upcoming_tournaments": total_upcoming_tournaments,
            "latest_news": latest_news,
            "member_count": member_count,
            "year_links": year_links,
            "lakes_data": lakes_data,
            "cancelled_tournaments": cancelled_tournaments,
        },
    )


@router.get("/")
async def page(request: Request, p: int = 1):
    return await home_paginated(request, p)


logger = get_logger(__name__)

EXCLUDED_EMAIL_DOMAINS = ("@sabc.com", "@saustinbc.com")

# Cloudflare Turnstile CAPTCHA
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def _verify_turnstile(token: str, remote_ip: str | None = None) -> bool:
    """Verify a Cloudflare Turnstile token. Returns True if valid."""
    if not TURNSTILE_SECRET_KEY:
        # Turnstile not configured — skip verification
        return True
    if not token:
        return False
    try:
        async with httpx.AsyncClient() as client:
            payload: Dict[str, str] = {"secret": TURNSTILE_SECRET_KEY, "response": token}
            if remote_ip:
                payload["remoteip"] = remote_ip
            resp = await client.post(TURNSTILE_VERIFY_URL, data=payload, timeout=5.0)
            result = resp.json()
            return bool(result.get("success", False))
    except (httpx.HTTPError, ValueError, KeyError) as e:
        logger.error(f"Turnstile verification failed: {e}")
        # Fail open — don't block legitimate users if Cloudflare is down
        return True


# Minimum seconds between form load and submit. Real humans take 30+ seconds to
# write a contact message; bots (including LLM agents) typically submit in <5s.
MIN_SUBMIT_TIME_SECONDS = 10
# Patterns that indicate spam content
SPAM_URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
# Phrases common in solicitor/marketing/SEO outreach. Triggering 2+ marks as spam;
# single matches are tolerated since real users may use these phrases coincidentally.
SOLICITOR_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in (
        r"\bi (?:represent|am writing on behalf)\b",
        r"\b(?:noticed|came across|stumbled upon|visited) your (?:website|site)\b",
        r"\b(?:boost|improve|increase) your (?:ranking|seo|traffic|visibility)\b",
        r"\b(?:seo|search engine optimization) services\b",
        r"\b(?:digital marketing|web (?:design|development)) services\b",
        r"\b(?:guest post|backlink|link[- ]building|do[- ]?follow)\b",
        r"\bour (?:team|agency|company) can (?:help|offer|provide)\b",
        r"\bfree (?:consultation|quote|audit|trial)\b",
        r"\bpersonal injury\b",
        r"\b(?:accident|injury) (?:attorney|lawyer)\b",
        r"\b(?:purchase|buy|acquire) your domain\b",
        r"\binterested in (?:buying|purchasing|acquiring) (?:your|the) (?:site|domain|website)\b",
        r"\bgenerate (?:more )?(?:leads|sales|revenue)\b",
        r"\bno obligation\b",
    )
]


def _is_spam_submission(
    honeypot: str,
    honeypot_alt: str,
    form_loaded_at: str,
    sender_name: str,
    subject: str,
    message: str,
) -> str | None:
    """Check if a contact form submission is spam.

    Returns a reason string if spam, None if legitimate.
    """
    # Honeypot checks - bots fill hidden fields that humans can't see
    if honeypot:
        return "honeypot filled"
    if honeypot_alt:
        return "alt honeypot filled"

    # Time-based check - bots submit forms faster than humans can type
    try:
        loaded_at = int(form_loaded_at)
        elapsed = int(time.time()) - loaded_at
        if elapsed < MIN_SUBMIT_TIME_SECONDS:
            return f"submitted too fast ({elapsed}s)"
    except (ValueError, TypeError):
        return "missing timestamp"

    # Content checks - common spam patterns
    if SPAM_URL_PATTERN.search(sender_name):
        return "URL in name field"

    # Reject messages that are just a URL with no real content
    message_without_urls = SPAM_URL_PATTERN.sub("", message).strip()
    if len(message_without_urls) < 10:
        return "message is mostly URLs"

    # Solicitor / marketing outreach detection
    combined = f"{subject}\n{message}"
    matches = [pat.pattern for pat in SOLICITOR_PATTERNS if pat.search(combined)]
    if len(matches) >= 2:
        return f"solicitor patterns matched: {len(matches)}"

    return None


@router.post("/about/contact")
async def contact_form(request: Request) -> RedirectResponse:
    """Handle contact form submission - sends email to all admins."""
    form = await request.form()
    sender_name = str(form.get("name", "")).strip()
    sender_email = str(form.get("email", "")).strip()
    subject_line = str(form.get("subject", "")).strip()
    message = str(form.get("message", "")).strip()

    if not all([sender_name, sender_email, subject_line, message]):
        return error_redirect("/about", "All fields are required.")

    # Spam protection checks
    honeypot = str(form.get("website", "")).strip()
    honeypot_alt = str(form.get("phone", "")).strip()
    form_loaded_at = str(form.get("form_loaded_at", "")).strip()
    spam_reason = _is_spam_submission(
        honeypot, honeypot_alt, form_loaded_at, sender_name, subject_line, message
    )
    if spam_reason:
        logger.warning(f"Spam contact form blocked: {spam_reason} (from {sender_email})")
        # Return success message to not tip off bots
        return success_redirect("/about", "Your message has been sent! We'll get back to you soon.")

    # Cloudflare Turnstile CAPTCHA verification
    # When the site key is configured, the widget was shown to the user,
    # so we must require a valid token (fail closed).
    turnstile_token = str(form.get("cf-turnstile-response", "")).strip()
    if TURNSTILE_SITE_KEY and not turnstile_token:
        logger.warning(f"Turnstile token missing (from {sender_email})")
        return error_redirect("/about", "CAPTCHA verification failed. Please try again.")
    if TURNSTILE_SECRET_KEY:
        client_ip = request.client.host if request.client else None
        if not await _verify_turnstile(turnstile_token, client_ip):
            logger.warning(f"Turnstile verification failed (from {sender_email})")
            return error_redirect("/about", "CAPTCHA verification failed. Please try again.")

    # Get admin emails, excluding placeholder domains
    with get_session() as session:
        admin_emails: List[str] = [
            email
            for (email,) in session.query(Angler.email)
            .filter(Angler.is_admin == True, Angler.email.isnot(None))  # noqa: E712
            .all()
            if email
            and not any(email.lower().endswith(domain) for domain in EXCLUDED_EMAIL_DOMAINS)
        ]

    if not admin_emails:
        logger.warning("No admin emails found for contact form submission")
        return error_redirect("/about", "Unable to send message. Please try again later.")

    success = send_contact_email(
        admin_emails=admin_emails,
        sender_name=sender_name,
        sender_email=sender_email,
        subject_line=subject_line,
        message=message,
    )

    if success:
        return success_redirect("/about", "Your message has been sent! We'll get back to you soon.")
    return error_redirect("/about", "Failed to send message. Please try again later.")


@router.get("/{page:path}")
async def static_page(request: Request, page: str):
    user = get_user_optional(request)
    if page in ["about", "bylaws"]:
        context: Dict[str, Any] = {"user": user}
        if page == "about":
            context["form_loaded_at"] = str(int(time.time()))
            context["turnstile_site_key"] = TURNSTILE_SITE_KEY
        return templates.TemplateResponse(request, f"{page}.html", context)
    raise HTTPException(status_code=404, detail="Page not found")
