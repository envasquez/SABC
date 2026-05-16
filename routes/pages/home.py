import json
import os
import re
import time
from datetime import date
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy import case, func
from sqlalchemy.orm import Query, Session, aliased

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
from core.helpers.forms import is_valid_email
from core.helpers.logging import get_logger
from core.helpers.pagination import PaginationState
from core.helpers.poll_day_info import get_poll_day_info
from core.helpers.response import error_redirect, success_redirect
from core.helpers.timezone import now_local
from core.query_service import QueryService
from core.types import UserDict
from routes.dependencies import get_lakes_list

router = APIRouter()

logger = get_logger(__name__)

# Rate limiter (disabled under tests, matching routes/auth/*).
is_test_env = os.environ.get("ENVIRONMENT") == "test"
limiter = Limiter(key_func=get_remote_address, enabled=not is_test_env)

EXCLUDED_EMAIL_DOMAINS = ("@sabc.com", "@saustinbc.com")

# Cloudflare Turnstile CAPTCHA
TURNSTILE_SITE_KEY = os.environ.get("TURNSTILE_SITE_KEY", "")
TURNSTILE_SECRET_KEY = os.environ.get("TURNSTILE_SECRET_KEY", "")
TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

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

# Number of completed tournaments shown per homepage page.
ITEMS_PER_PAGE = 4
# Maximum number of numbered page links rendered in the pagination control.
MAX_PAGES_SHOWN = 5


def build_tournament_query(
    session: Session, complete_filter: Optional[bool] = None
) -> "Query[Any]":
    """Build the base homepage tournament query.

    Selects per-tournament event/lake/ramp detail columns plus aggregated
    angler/fish/weight totals. When ``complete_filter`` is provided the query
    is further filtered on ``Tournament.complete``.

    Args:
        session: Active database session.
        complete_filter: If not None, restrict to tournaments whose
            ``complete`` flag equals this value.

    Returns:
        A SQLAlchemy ``Query`` ready for additional filtering/ordering.
    """
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


def _fetch_homepage_tournaments(session: Session, offset: int) -> tuple[List[Any], int]:
    """Fetch the completed (paginated) + upcoming tournament rows for the homepage.

    Args:
        session: Active database session.
        offset: Row offset for the paginated completed-tournament slice.

    Returns:
        A ``(tournament_rows, total_upcoming)`` tuple where ``tournament_rows``
        is the completed page concatenated with all upcoming tournaments.
    """
    # Get COMPLETED SABC tournaments with pagination (includes cancelled tournaments)
    completed_tournaments_query = (
        build_tournament_query(session)
        .filter(Event.event_type == "sabc_tournament")
        .filter((Tournament.complete.is_(True)) | (Event.is_cancelled.is_(True)))
        .order_by(Event.date.desc())
        .limit(ITEMS_PER_PAGE)
        .offset(offset)
        .all()
    )

    # Get ALL UPCOMING tournaments (no pagination), excludes cancelled ones
    upcoming_tournaments_query = (
        build_tournament_query(session, complete_filter=False)
        .filter(Event.is_cancelled.isnot(True))
        .order_by(Event.date.asc())
        .all()
    )

    total_upcoming_tournaments = len(upcoming_tournaments_query)
    tournaments_query = list(completed_tournaments_query) + list(upcoming_tournaments_query)
    return tournaments_query, total_upcoming_tournaments


def _fetch_top_results(session: Session, tournament_ids: List[int]) -> Dict[int, List[Any]]:
    """Fetch the top-3 team results for each tournament.

    Sorts by ``(tournament_id, place_finish)`` and slices to 3 per tournament
    in Python — cheaper than N LIMIT-3 round trips, and order is preserved.
    The "Admin User" filter (default admin who should never appear on the
    homepage podium) is preserved verbatim.

    Args:
        session: Active database session.
        tournament_ids: Tournament IDs to fetch results for.

    Returns:
        Mapping of tournament_id -> list of up-to-3 result tuples of shape
        ``(place_finish, angler1_name, angler2_name, total_weight, team_size)``.
    """
    top_results_by_tid: Dict[int, List[Any]] = {tid: [] for tid in tournament_ids}
    if not tournament_ids:
        return top_results_by_tid

    Angler1 = aliased(Angler)
    Angler2 = aliased(Angler)
    all_top_results = (
        session.query(
            TeamResult.tournament_id,
            TeamResult.place_finish,
            Angler1.name.label("angler1_name"),
            Angler2.name.label("angler2_name"),
            TeamResult.total_weight,
            case((TeamResult.angler2_id.is_(None), 1), else_=2).label("team_size"),
        )
        .join(Angler1, TeamResult.angler1_id == Angler1.id)
        .outerjoin(Angler2, TeamResult.angler2_id == Angler2.id)
        .filter(
            TeamResult.tournament_id.in_(tournament_ids),
            Angler1.name != "Admin User",
            (Angler2.name != "Admin User") | (Angler2.name.is_(None)),
        )
        .order_by(TeamResult.tournament_id.asc(), TeamResult.place_finish.asc())
        .all()
    )
    for row in all_top_results:
        bucket = top_results_by_tid[row.tournament_id]
        if len(bucket) < 3:
            # Strip the tournament_id prefix so the row shape stays
            # (place_finish, a1_name, a2_name, total_weight, team_size)
            # — the template indexes result[0]..result[3], so the
            # positional shape must match the original query exactly.
            bucket.append(
                (
                    row.place_finish,
                    row.angler1_name,
                    row.angler2_name,
                    row.total_weight,
                    row.team_size,
                )
            )
    return top_results_by_tid


def _fetch_poll_data(
    session: Session, poll_ids: List[int], user: Optional[UserDict]
) -> tuple[Dict[int, Poll], Dict[int, List[Any]], set[int]]:
    """Batch-fetch poll metadata for the homepage tournament cards.

    Args:
        session: Active database session.
        poll_ids: Poll IDs referenced by the visible tournaments.
        user: The current user, or None for anonymous visitors.

    Returns:
        A tuple ``(polls_by_id, options_by_poll, user_voted_polls)``.
    """
    # Polls keyed by id (for starts_at/closes_at status check).
    polls_by_id: Dict[int, Poll] = {}
    if poll_ids:
        polls_by_id = {p.id: p for p in session.query(Poll).filter(Poll.id.in_(poll_ids)).all()}

    # Poll options + vote counts bucketed by poll_id. Identical
    # outerjoin+group_by shape to the original per-poll query.
    options_by_poll: Dict[int, List[Any]] = {pid: [] for pid in poll_ids}
    if poll_ids:
        all_poll_options = (
            session.query(
                PollOption.poll_id,
                PollOption.id,
                PollOption.option_text,
                PollOption.option_data,
                func.count(PollVote.id).label("vote_count"),
            )
            .outerjoin(PollVote, PollOption.id == PollVote.option_id)
            .filter(PollOption.poll_id.in_(poll_ids))
            .group_by(
                PollOption.poll_id,
                PollOption.id,
                PollOption.option_text,
                PollOption.option_data,
            )
            .all()
        )
        for opt in all_poll_options:
            options_by_poll[opt.poll_id].append(opt)

    # Which polls has the current user voted in? Only query when a
    # user is logged in — anonymous visitors can never have a vote row.
    user_voted_polls: set[int] = set()
    if user and poll_ids:
        user_id = user.get("id")
        user_voted_polls = {
            pv.poll_id
            for pv in session.query(PollVote.poll_id)
            .filter(PollVote.poll_id.in_(poll_ids), PollVote.angler_id == user_id)
            .all()
        }

    return polls_by_id, options_by_poll, user_voted_polls


def _assemble_tournament_card(
    tournament: Any,
    user: Optional[UserDict],
    top_results_by_tid: Dict[int, List[Any]],
    polls_by_id: Dict[int, Poll],
    options_by_poll: Dict[int, List[Any]],
    user_voted_polls: set[int],
    now: Any,
) -> Dict[str, Any]:
    """Build the template context dict for a single tournament card.

    Args:
        tournament: A tournament row from ``build_tournament_query``.
        user: The current user, or None for anonymous visitors.
        top_results_by_tid: Top-3 results keyed by tournament id.
        polls_by_id: Poll objects keyed by id.
        options_by_poll: Poll options keyed by poll id.
        user_voted_polls: Set of poll ids the current user has voted in.
        now: Current local time, or None when there are no polls.

    Returns:
        A dict consumed by the homepage tournament card template.
    """
    tournament_id = tournament.id
    poll_id = tournament.poll_id

    top_results_query = top_results_by_tid.get(tournament_id, [])

    # Get poll data and check if user has voted
    poll_data = None
    user_has_voted = False
    poll_is_open = False

    if poll_id:
        poll = polls_by_id.get(poll_id)
        # Poll datetimes are already timezone-aware from database
        if poll and poll.starts_at and poll.closes_at and now is not None:
            poll_is_open = poll.starts_at <= now <= poll.closes_at

        poll_options = options_by_poll.get(poll_id, [])

        # Check if user has voted. get_user_optional always returns a
        # UserDict (or None) — the previous defensive isinstance check
        # was lying to the type system.
        if user:
            user_has_voted = poll_id in user_voted_polls

        # Show poll data if user has voted OR if poll is closed (results are public)
        if (user_has_voted or not poll_is_open) and poll_options:
            poll_data = []
            for opt in poll_options:
                try:
                    option_data_dict = json.loads(opt.option_data) if opt.option_data else {}
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
    tournament_date = tournament.date
    is_past = tournament_date < date.today() if tournament_date else False

    # Sunrise + forecast for upcoming, non-cancelled tournaments. Sunrise
    # is always available; weather is only populated within the NWS
    # forecast window (~7 days), otherwise the weather field is None.
    day_info: Any = None
    is_cancelled = tournament.is_cancelled or False
    if not is_past and not is_cancelled and tournament_date:
        try:
            day_info = get_poll_day_info(tournament_date)
        except Exception as e:
            logger.warning(f"day info lookup failed for tournament {tournament.id}: {e}")

    return {
        "id": tournament.id,
        "date": tournament_date,
        "name": tournament.name,
        "description": tournament.description,
        "lake_display_name": tournament.lake_display_name,
        "lake_name": tournament.lake_name,
        "ramp_name": tournament.ramp_name,
        "ramp_google_maps": tournament.ramp_google_maps,
        "lake_google_maps": tournament.lake_google_maps,
        "google_maps_iframe": tournament.ramp_google_maps or tournament.lake_google_maps,
        "start_time": tournament.start_time,
        "end_time": tournament.end_time,
        "entry_fee": tournament.entry_fee or 50.0,
        "fish_limit": tournament.fish_limit or 5,
        "limit_type": tournament.limit_type or "per_person",
        "is_team": tournament.is_team,
        "is_paper": tournament.is_paper,
        "complete": tournament.complete,
        "is_past": is_past,  # True if date has passed, regardless of complete status
        "poll_id": poll_id,
        "total_anglers": tournament.total_anglers or 0,
        "total_fish": tournament.total_fish or 0,
        "total_weight": tournament.total_weight or 0.0,
        "aoy_points": tournament.aoy_points if tournament.aoy_points is not None else True,
        "event_type": tournament.event_type,
        "is_cancelled": is_cancelled,
        "day_info": day_info,
        "top_results": top_results_query,
        "poll_data": poll_data,
        "user_has_voted": user_has_voted,
        "poll_is_open": poll_is_open,
    }


def _fetch_cancelled_tournaments(session: Session) -> List[Dict[str, Any]]:
    """Fetch upcoming cancelled SABC tournaments for the alert banner.

    Args:
        session: Active database session.

    Returns:
        List of cancelled-tournament dicts for the banner.
    """
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
    return [
        {
            "id": ct[0],
            "date": ct[1],
            "name": ct[2],
            "description": ct[3],
            "lake_name": ct[4],
        }
        for ct in cancelled_tournaments_query
    ]


def _fetch_latest_news(session: Session) -> List[Any]:
    """Fetch the latest published, non-archived, non-expired news items.

    Excludes admin@sabc.com from author display (default admin user).

    Args:
        session: Active database session.

    Returns:
        Up to 5 news rows ordered by priority then recency.
    """
    Author = aliased(Angler)
    Editor = aliased(Angler)
    return (
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


def _compute_page_range(page: int, total_pages: int) -> range:
    """Compute the range of numbered page links to show in pagination.

    Shows up to ``MAX_PAGES_SHOWN`` page numbers, centered on the current
    page where possible and clamped near the start/end.

    Args:
        page: The current page number.
        total_pages: Total number of pages.

    Returns:
        A ``range`` of page numbers to render.
    """
    half_range = MAX_PAGES_SHOWN // 2

    if total_pages <= MAX_PAGES_SHOWN:
        return range(1, total_pages + 1)

    start_page = max(1, page - half_range)
    end_page = min(total_pages, page + half_range)

    # Adjust if we're near the start or end
    if end_page - start_page + 1 < MAX_PAGES_SHOWN:
        if start_page == 1:
            end_page = min(total_pages, start_page + MAX_PAGES_SHOWN - 1)
        else:
            start_page = max(1, end_page - MAX_PAGES_SHOWN + 1)

    return range(start_page, end_page + 1)


async def home_paginated(request: Request, page: int = 1) -> Response:
    user = get_user_optional(request)

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
            items_per_page=ITEMS_PER_PAGE,
            total_items=total_completed_tournaments,
        )

        if pagination.is_out_of_range():
            return RedirectResponse(f"/?p={pagination.total_pages}", status_code=303)

        page = max(1, page)
        pagination = PaginationState(
            page=page,
            items_per_page=ITEMS_PER_PAGE,
            total_items=total_completed_tournaments,
        )
        offset = pagination.offset
        total_pages = pagination.total_pages

        # Fetch completed (paginated) + upcoming tournament rows.
        tournaments_query, total_upcoming_tournaments = _fetch_homepage_tournaments(session, offset)

        # Batch-fetch the per-tournament data the loop needs, so we don't
        # fire 3-4 queries per tournament card (was an N+1 burning 12+ round
        # trips for the typical 4-tournament homepage).
        tournament_ids = [t.id for t in tournaments_query]
        poll_ids = [t.poll_id for t in tournaments_query if t.poll_id]

        top_results_by_tid = _fetch_top_results(session, tournament_ids)
        polls_by_id, options_by_poll, user_voted_polls = _fetch_poll_data(session, poll_ids, user)

        now = now_local() if poll_ids else None

        tournaments_with_results: List[Dict[str, Any]] = [
            _assemble_tournament_card(
                tournament,
                user,
                top_results_by_tid,
                polls_by_id,
                options_by_poll,
                user_voted_polls,
                now,
            )
            for tournament in tournaments_query
        ]

        # Get member count (only members with current dues)
        member_count = (
            session.query(func.count(Angler.id))
            .filter(Angler.member.is_(True), Angler.dues_paid_through >= date.today())
            .scalar()
            or 0
        )

        cancelled_tournaments = _fetch_cancelled_tournaments(session)
        latest_news = _fetch_latest_news(session)

    # Pagination metadata (total_pages already calculated above)
    start_index = offset + 1
    end_index = min(offset + ITEMS_PER_PAGE, total_completed_tournaments)
    page_range = _compute_page_range(page, total_pages)

    # Get year navigation links
    with engine.connect() as conn:
        qs = QueryService(conn)
        year_links = qs.get_tournament_years_with_first_id(ITEMS_PER_PAGE)

    # Get lakes data for poll results rendering. Single LEFT JOIN query;
    # was previously 1 + N_lakes connections per home-page render.
    lakes_data = [
        {
            "id": lake["id"],
            "name": lake["display_name"],
            "ramps": [{"id": r["id"], "name": r["name"].title()} for r in lake["ramps"]],
        }
        for lake in get_lakes_list(with_ramps=True)
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
async def page(request: Request, p: int = 1) -> Response:
    return await home_paginated(request, p)


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
    except httpx.HTTPError as e:
        # Genuine connectivity error (Cloudflare unreachable) — fail open so
        # legitimate users aren't blocked by an outage outside our control.
        logger.error(f"Turnstile verification failed (connectivity): {e}")
        return True
    except (ValueError, KeyError) as e:
        # Malformed/unparseable response derived from attacker-controlled
        # input — fail closed so a forged token can't bypass CAPTCHA.
        logger.error(f"Turnstile verification failed (malformed response): {e}")
        return False


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
@limiter.limit("5/hour")
async def contact_form(request: Request) -> RedirectResponse:
    """Handle contact form submission - sends email to all admins."""
    form = await request.form()
    sender_name = str(form.get("name", "")).strip()
    sender_email = str(form.get("email", "")).strip()
    subject_line = str(form.get("subject", "")).strip()
    message = str(form.get("message", "")).strip()

    if not all([sender_name, sender_email, subject_line, message]):
        return error_redirect("/about", "All fields are required.")

    # Validate the sender address: it is placed into the Reply-To header,
    # so a malformed value (or one carrying CR/LF) must never reach the email.
    if not is_valid_email(sender_email):
        return error_redirect("/about", "Please enter a valid email address.")

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
async def static_page(request: Request, page: str) -> Response:
    user = get_user_optional(request)
    if page in ["about", "bylaws"]:
        context: Dict[str, Any] = {"user": user}
        if page == "about":
            context["form_loaded_at"] = str(int(time.time()))
            context["turnstile_site_key"] = TURNSTILE_SITE_KEY
        return templates.TemplateResponse(request, f"{page}.html", context)
    raise HTTPException(status_code=404, detail="Page not found")
