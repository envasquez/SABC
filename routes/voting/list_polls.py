from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import case, exists, false, func, select, true

from core.db_schema import Angler, Poll, PollVote, get_session
from core.deps import templates
from core.helpers.auth import require_auth
from core.helpers.timezone import now_local
from routes.dependencies import get_lakes_list, get_ramps_for_lake
from routes.voting.helpers import (
    get_poll_options,
    get_seasonal_tournament_history,
    process_closed_polls,
)

router = APIRouter()


@router.get("/polls")
async def polls(
    request: Request,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_auth),
    tab: str = "club",
    p: int = 1,
):
    # Only members can view polls
    if not user.get("member"):
        from fastapi import HTTPException

        raise HTTPException(status_code=403, detail="Only members can view polls")

    background_tasks.add_task(process_closed_polls)

    # Pagination settings
    items_per_page = 4
    page = max(1, p)  # Ensure page is at least 1

    with get_session() as session:
        # Get member count
        member_count = (
            session.query(func.count(Angler.id)).filter(Angler.member.is_(true())).scalar() or 0
        )

        # Build status case expression
        # Use naive datetime for database comparison (DB stores naive datetimes)
        now = now_local().replace(tzinfo=None)
        status_case = case(
            (Poll.starts_at > now, "upcoming"),
            (
                (Poll.starts_at <= now) & (Poll.closes_at >= now) & (Poll.closed.is_(false())),
                "active",
            ),
            else_="closed",
        )

        # Check if user has voted subquery
        user_voted_exists = exists(
            select(1).where(PollVote.poll_id == Poll.id).where(PollVote.angler_id == user["id"])
        )

        # Count active polls for each tab (for tab labels)
        active_club_polls = (
            session.query(func.count(Poll.id))
            .filter(
                Poll.poll_type != "tournament_location",
                Poll.starts_at <= now,
                Poll.closes_at >= now,
                Poll.closed.is_(false()),
            )
            .scalar()
            or 0
        )

        active_tournament_polls = (
            session.query(func.count(Poll.id))
            .filter(
                Poll.poll_type == "tournament_location",
                Poll.starts_at <= now,
                Poll.closes_at >= now,
                Poll.closed.is_(false()),
            )
            .scalar()
            or 0
        )

        # Count upcoming polls for each tab (for tab labels)
        upcoming_club_polls = (
            session.query(func.count(Poll.id))
            .filter(
                Poll.poll_type != "tournament_location",
                Poll.starts_at > now,
            )
            .scalar()
            or 0
        )

        upcoming_tournament_polls = (
            session.query(func.count(Poll.id))
            .filter(
                Poll.poll_type == "tournament_location",
                Poll.starts_at > now,
            )
            .scalar()
            or 0
        )

        # Base query for polls with status and voted flag
        base_query = select(
            Poll.id,
            Poll.title,
            Poll.description,
            Poll.closes_at,
            Poll.closed,
            Poll.poll_type,
            Poll.starts_at,
            Poll.event_id,
            status_case.label("status"),
            user_voted_exists.label("user_has_voted"),
        )

        # Filter by tab type
        if tab == "tournament":
            base_query = base_query.where(Poll.poll_type == "tournament_location")
        else:
            # Club polls - everything except tournament_location
            base_query = base_query.where(Poll.poll_type != "tournament_location")

        # Get total count for pagination
        count_query = select(func.count()).select_from(base_query.subquery())
        total_polls = session.execute(count_query).scalar() or 0

        # Calculate total pages and validate page number
        total_pages = (total_polls + items_per_page - 1) // items_per_page if total_polls > 0 else 1

        # Validate page is within bounds - redirect to last page if too high
        if page > total_pages and total_pages > 0:
            return RedirectResponse(f"/polls?tab={tab}&p={total_pages}", status_code=303)

        offset = (page - 1) * items_per_page

        # Apply ordering: active first, then upcoming, then closed (by date)
        # Order by status priority, then by start date
        status_order = case(
            (status_case == "active", 1),
            (status_case == "upcoming", 2),
            (status_case == "closed", 3),
        )
        polls_query = (
            base_query.order_by(status_order, Poll.starts_at.desc())
            .limit(items_per_page)
            .offset(offset)
        )
        polls_data = session.execute(polls_query).all()

        # Fetch all vote counts in a single query to avoid N+1
        poll_ids = [poll_row.id for poll_row in polls_data]
        vote_counts_query = (
            select(PollVote.poll_id, func.count(func.distinct(PollVote.angler_id)).label("count"))
            .where(PollVote.poll_id.in_(poll_ids))
            .group_by(PollVote.poll_id)
        )
        vote_counts_data = session.execute(vote_counts_query).all()
        vote_counts = {row[0]: row[1] for row in vote_counts_data}

        # Build polls list with vote counts
        polls: List[Dict[str, Any]] = []
        for poll_row in polls_data:
            # Get vote count from pre-fetched data
            unique_voters = vote_counts.get(poll_row.id, 0)

            # Get seasonal history for tournament polls
            seasonal_history = []
            if poll_row.poll_type == "tournament_location":
                poll_obj = session.query(Poll).filter(Poll.id == poll_row.id).first()
                if poll_obj:
                    seasonal_history = get_seasonal_tournament_history(session, poll_obj)

            polls.append(
                {
                    "id": poll_row.id,
                    "title": poll_row.title,
                    "description": poll_row.description if poll_row.description else "",
                    "closes_at": poll_row.closes_at,
                    "starts_at": poll_row.starts_at,
                    "closed": bool(poll_row.closed),
                    "poll_type": poll_row.poll_type,
                    "event_id": poll_row.event_id,
                    "status": poll_row.status,
                    "user_has_voted": bool(poll_row.user_has_voted),
                    "options": get_poll_options(poll_row.id, bool(user.get("is_admin"))),
                    "member_count": member_count,
                    "unique_voters": unique_voters,
                    "participation_percent": round(
                        (unique_voters / member_count * 100) if member_count > 0 else 0, 1
                    ),
                    "seasonal_history": seasonal_history,
                }
            )

    # Calculate pagination metadata (total_pages already calculated above)
    start_index = offset + 1 if total_polls > 0 else 0
    end_index = min(offset + items_per_page, total_polls)

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

    # Get all members for admin proxy voting dropdown
    with get_session() as session:
        all_members = (
            session.query(Angler.id, Angler.name, Angler.email)
            .filter(Angler.member.is_(true()))
            .order_by(Angler.name)
            .all()
        )
        members_list = [{"id": m.id, "name": m.name, "email": m.email} for m in all_members]

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
        "polls.html",
        {
            "request": request,
            "user": user,
            "polls": polls,
            "members": members_list,
            "lakes_data": lakes_data,
            "current_tab": tab,
            "current_page": page,
            "total_pages": total_pages,
            "page_range": page_range,
            "start_index": start_index,
            "end_index": end_index,
            "total_polls": total_polls,
            "active_club_polls": active_club_polls,
            "active_tournament_polls": active_tournament_polls,
            "upcoming_club_polls": upcoming_club_polls,
            "upcoming_tournament_polls": upcoming_tournament_polls,
        },
    )
