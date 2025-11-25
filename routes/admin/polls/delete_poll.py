from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from core.db_schema import Angler, Poll, PollOption, PollVote, get_session
from core.helpers.auth import require_admin
from core.helpers.crud import bulk_delete, delete_entity
from core.helpers.logging import get_logger
from core.helpers.response import sanitize_error_message

router = APIRouter()
logger = get_logger("admin.polls")


def _delete_poll_cascade(session: Session, poll_id: int) -> None:
    """Delete poll votes and options before deleting poll."""
    bulk_delete(session, PollVote, [PollVote.poll_id == poll_id])
    bulk_delete(session, PollOption, [PollOption.poll_id == poll_id])


@router.delete("/admin/polls/{poll_id}")
async def delete_poll(request: Request, poll_id: int) -> Response:
    """Delete a poll and all associated votes and options."""
    return delete_entity(
        request,
        poll_id,
        Poll,
        success_message="Poll deleted successfully",
        error_message="Failed to delete poll",
        pre_delete_hook=_delete_poll_cascade,
    )


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
