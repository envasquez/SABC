from typing import Any, Dict, List

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import case, exists, false, func, select, true

from core.db_schema import Angler, Poll, PollVote, get_session
from core.deps import templates
from core.helpers.auth import require_auth
from core.helpers.timezone import now_local
from routes.dependencies import get_lakes_list, get_ramps_for_lake
from routes.voting.helpers import get_poll_options, process_closed_polls

router = APIRouter()


@router.get("/polls")
async def polls(
    request: Request,
    background_tasks: BackgroundTasks,
    user: Dict[str, Any] = Depends(require_auth),
):
    background_tasks.add_task(process_closed_polls)

    with get_session() as session:
        # Get member count
        member_count = (
            session.query(func.count(Angler.id)).filter(Angler.member.is_(true())).scalar() or 0
        )

        # Build status case expression
        now = now_local()
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

        # Query polls with status and voted flag
        polls_query = select(
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
        ).order_by(Poll.starts_at.asc())

        polls_data = session.execute(polls_query).all()

        # Build polls list with vote counts
        polls: List[Dict[str, Any]] = []
        for poll_row in polls_data:
            # Get unique voters count for this poll
            unique_voters = (
                session.query(func.count(func.distinct(PollVote.angler_id)))
                .filter(PollVote.poll_id == poll_row.id)
                .scalar()
                or 0
            )

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
                    "options": get_poll_options(poll_row.id, user.get("is_admin")),
                    "member_count": member_count,
                    "unique_voters": unique_voters,
                    "participation_percent": round(
                        (unique_voters / member_count * 100) if member_count > 0 else 0, 1
                    ),
                }
            )

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
        "polls.html", {"request": request, "user": user, "polls": polls, "lakes_data": lakes_data}
    )
