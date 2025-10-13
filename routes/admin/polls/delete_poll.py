from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.db_schema import Angler, Poll, PollOption, PollVote, get_session
from core.helpers.auth import require_admin
from core.helpers.logging import get_logger
from core.helpers.response import sanitize_error_message

router = APIRouter()
logger = get_logger("admin.polls")


@router.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int):
    _user = require_admin(request)
    try:
        with get_session() as session:
            # Delete poll votes
            session.query(PollVote).filter(PollVote.poll_id == poll_id).delete()

            # Delete poll options
            session.query(PollOption).filter(PollOption.poll_id == poll_id).delete()

            # Delete poll
            session.query(Poll).filter(Poll.id == poll_id).delete()

            # Context manager will commit automatically on successful exit

        return JSONResponse({"success": True})
    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to delete poll")
        return JSONResponse({"error": error_msg}, status_code=500)


@router.delete("/admin/votes/{vote_id}")
async def delete_vote(request: Request, vote_id: int):
    _user = require_admin(request)
    try:
        with get_session() as session:
            # Get vote details before deletion
            vote = (
                session.query(PollVote)
                .join(Angler, PollVote.angler_id == Angler.id)
                .join(PollOption, PollVote.option_id == PollOption.id)
                .join(Poll, PollVote.poll_id == Poll.id)
                .filter(PollVote.id == vote_id)
                .with_entities(PollVote.id, Angler.name, PollOption.option_text, Poll.title)
                .first()
            )

            if not vote:
                return JSONResponse({"error": "Vote not found"}, status_code=404)

            # Delete the vote
            session.query(PollVote).filter(PollVote.id == vote_id).delete()

        return JSONResponse(
            {
                "success": True,
                "message": f"Deleted vote by {vote[1]} for '{vote[2]}' in poll '{vote[3]}'",
            },
            status_code=200,
        )
    except Exception as e:
        error_msg = sanitize_error_message(e, "Failed to delete vote")
        return JSONResponse({"error": error_msg}, status_code=500)
