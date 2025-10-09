import json
from typing import Any, Dict

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from core.db_schema import Poll, PollOption, PollVote, get_session
from core.helpers.auth import require_auth
from core.helpers.logging import get_logger
from core.helpers.response import sanitize_error_message
from core.helpers.timezone import now_local
from routes.voting.vote_validation import (
    get_or_create_option_id,
    validate_poll_state,
    validate_tournament_location_vote,
)

router = APIRouter()
logger = get_logger("voting")


@router.post("/polls/{poll_id}/vote")
async def vote_in_poll(
    request: Request,
    poll_id: int,
    option_id: str = Form(),
    user: Dict[str, Any] = Depends(require_auth),
) -> RedirectResponse:
    if not user.get("member"):
        return RedirectResponse("/polls?error=Only members can vote", status_code=302)

    try:
        error = validate_poll_state(poll_id, user["id"])
        if error:
            return RedirectResponse(f"/polls?error={error}", status_code=302)

        with get_session() as session:
            # Get poll type
            poll = session.query(Poll).filter(Poll.id == poll_id).first()
            if not poll:
                return RedirectResponse("/polls?error=Invalid poll", status_code=302)

            poll_type = poll.poll_type

            if poll_type == "tournament_location":
                try:
                    vote_data = json.loads(option_id)
                except (json.JSONDecodeError, ValueError):
                    return RedirectResponse("/polls?error=Invalid vote data", status_code=302)

                option_text, error = validate_tournament_location_vote(vote_data)
                if error or not option_text:
                    return RedirectResponse(
                        f"/polls?error={error or 'Invalid vote data'}", status_code=302
                    )
                actual_option_id = get_or_create_option_id(poll_id, option_text, vote_data)
            else:
                try:
                    actual_option_id = int(option_id)
                except ValueError:
                    return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

                # Validate option exists for this poll
                option_exists = (
                    session.query(PollOption)
                    .filter(PollOption.id == actual_option_id)
                    .filter(PollOption.poll_id == poll_id)
                    .first()
                )
                if not option_exists:
                    return RedirectResponse("/polls?error=Invalid option selected", status_code=302)

            # Cast vote
            new_vote = PollVote(
                poll_id=poll_id,
                option_id=actual_option_id,
                angler_id=user["id"],
                voted_at=now_local(),
            )
            session.add(new_vote)

        return RedirectResponse("/polls?success=Vote cast successfully", status_code=302)
    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to cast vote. Please try again.")
        return RedirectResponse(f"/polls?error={error_msg}", status_code=302)
