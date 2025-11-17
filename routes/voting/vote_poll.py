import json
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from core.db_schema import Poll, PollOption, PollVote, get_session
from core.helpers.auth import require_auth
from core.helpers.logging import get_logger
from core.helpers.response import sanitize_error_message
from core.helpers.timezone import now_local
from routes.voting.vote_validation import (
    get_or_create_option_id,
    validate_proxy_vote,
    validate_tournament_location_vote,
)

router = APIRouter()
logger = get_logger("voting")


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(
    request: Request,
    poll_id: int,
    option_id: str = Form(),
    vote_as_angler_id: Optional[int] = Form(None),
    user: Dict[str, Any] = Depends(require_auth),
) -> RedirectResponse:
    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=303)

    # Determine if this is a proxy vote (admin voting on behalf of someone)
    is_proxy_vote = vote_as_angler_id is not None and user.get("is_admin", False)
    voting_for_angler_id = vote_as_angler_id if is_proxy_vote else user["id"]
    target_angler_name = None

    try:
        with get_session() as session:
            # Acquire row lock on poll to prevent concurrent voting issues
            poll = (
                session.query(Poll)
                .filter(Poll.id == poll_id)
                .with_for_update()  # Lock the poll row
                .first()
            )

            if not poll:
                return RedirectResponse("/polls?error=Invalid poll", status_code=303)

            # Validate proxy vote if applicable
            if is_proxy_vote:
                # Non-admins cannot cast proxy votes
                if not user.get("is_admin", False):
                    logger.warning(
                        "Non-admin attempted proxy vote",
                        extra={
                            "poll_id": poll_id,
                            "user_id": user["id"],
                            "target_id": vote_as_angler_id,
                        },
                    )
                    return RedirectResponse(
                        "/polls?error=Only admins can vote on behalf of members", status_code=303
                    )

                admin_id = int(user["id"]) if isinstance(user.get("id"), (int, str)) else 0
                target_angler_name, error = validate_proxy_vote(
                    admin_id, voting_for_angler_id, poll_id, session
                )
                if error:
                    return RedirectResponse(f"/polls?error={error}", status_code=303)

            # Check for existing vote with lock to prevent race condition
            existing_vote = (
                session.query(PollVote)
                .filter(PollVote.poll_id == poll_id, PollVote.angler_id == voting_for_angler_id)
                .with_for_update()  # Lock if exists
                .first()
            )

            if existing_vote:
                logger.info(
                    "User attempted to vote twice in same poll",
                    extra={"poll_id": poll_id, "user_id": user["id"]},
                )
                return RedirectResponse(
                    "/polls?error=You have already voted in this poll", status_code=303
                )

            # Validate poll is currently active (time window check)
            current_time = now_local()
            if not (poll.starts_at <= current_time <= poll.closes_at):
                logger.info(
                    "Vote attempted on inactive poll",
                    extra={
                        "poll_id": poll_id,
                        "user_id": user["id"],
                        "poll_starts": poll.starts_at,
                        "poll_closes": poll.closes_at,
                        "current_time": current_time,
                    },
                )
                return RedirectResponse(
                    "/polls?error=This poll is not currently active", status_code=303
                )

            poll_type = poll.poll_type

            # Process vote data based on poll type
            if poll_type == "tournament_location":
                try:
                    vote_data = json.loads(option_id)
                except (json.JSONDecodeError, ValueError):
                    return RedirectResponse("/polls?error=Invalid vote data", status_code=303)

                option_text, error = validate_tournament_location_vote(vote_data)
                if error or not option_text:
                    return RedirectResponse(
                        f"/polls?error={error or 'Invalid vote data'}", status_code=303
                    )
                actual_option_id = get_or_create_option_id(poll_id, option_text, vote_data, session)
            else:
                try:
                    actual_option_id = int(option_id)
                except (ValueError, TypeError):
                    logger.error(
                        "Invalid option_id format",
                        extra={"poll_id": poll_id, "user_id": user["id"], "option_id": option_id},
                    )
                    return RedirectResponse("/polls?error=Invalid option selected", status_code=303)

                # Validate option exists for this poll
                option_exists = (
                    session.query(PollOption)
                    .filter(PollOption.id == actual_option_id)
                    .filter(PollOption.poll_id == poll_id)
                    .first()
                )
                if not option_exists:
                    logger.warning(
                        "Vote attempted for non-existent option - poll may have been edited",
                        extra={
                            "poll_id": poll_id,
                            "user_id": user["id"],
                            "option_id": actual_option_id,
                        },
                    )
                    return RedirectResponse(
                        "/polls?error=This poll was recently updated. Please refresh and try again.",
                        status_code=303,
                    )

            # Cast vote with IntegrityError handling
            try:
                new_vote = PollVote(
                    poll_id=poll_id,
                    option_id=actual_option_id,
                    angler_id=voting_for_angler_id,
                    voted_at=current_time,
                    cast_by_admin=is_proxy_vote,
                    cast_by_admin_id=user["id"] if is_proxy_vote else None,
                )
                session.add(new_vote)
                session.flush()  # Ensure vote is written to database
                vote_id = new_vote.id  # Verify we got an ID back from the database

                if not vote_id:
                    logger.error(
                        "Vote creation failed - no ID returned",
                        extra={"poll_id": poll_id, "user_id": user["id"]},
                    )
                    return RedirectResponse("/polls?error=Failed to record vote", status_code=303)

                if is_proxy_vote:
                    logger.info(
                        "Admin cast proxy vote",
                        extra={
                            "admin_id": user["id"],
                            "admin_name": user.get("name"),
                            "voted_for_angler_id": voting_for_angler_id,
                            "voted_for_name": target_angler_name,
                            "poll_id": poll_id,
                            "vote_id": vote_id,
                        },
                    )
                else:
                    logger.info(
                        "Vote cast successfully",
                        extra={"poll_id": poll_id, "user_id": user["id"], "vote_id": vote_id},
                    )

            except IntegrityError as e:
                # Database constraint prevented duplicate vote
                # This is a fallback - the earlier check should catch this
                logger.warning(
                    "Duplicate vote prevented by database constraint",
                    extra={"poll_id": poll_id, "user_id": user["id"], "error": str(e)},
                )
                return RedirectResponse(
                    "/polls?error=You have already voted in this poll", status_code=303
                )

        return RedirectResponse("/polls?success=Vote cast successfully", status_code=303)

    except IntegrityError as e:
        # Handle any other integrity errors at outer level
        logger.error(
            "Database integrity error during voting",
            extra={"poll_id": poll_id, "user_id": user["id"], "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse(
            "/polls?error=Unable to cast vote. Please try again.", status_code=303
        )

    except SQLAlchemyError as e:
        logger.error(
            "Database error during voting",
            extra={"poll_id": poll_id, "user_id": user["id"], "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse("/polls?error=Database error. Please try again.", status_code=303)

    except (json.JSONDecodeError, ValueError) as e:
        logger.warning(
            "Invalid vote data format",
            extra={"poll_id": poll_id, "user_id": user["id"], "error": str(e)},
        )
        return RedirectResponse("/polls?error=Invalid vote data", status_code=303)

    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to cast vote. Please try again.")
        logger.critical(
            "Unexpected error during voting",
            extra={"poll_id": poll_id, "user_id": user.get("id"), "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse(f"/polls?error={error_msg}", status_code=303)
