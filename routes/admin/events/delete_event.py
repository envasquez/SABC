from typing import Optional

from fastapi import APIRouter, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.db_schema import Event, Poll, PollOption, PollVote, Result, Tournament
from core.helpers.crud import bulk_delete, delete_entity

router = APIRouter()


def _check_event_has_results(session: Session, event_id: int) -> Optional[str]:
    """Check if event has tournament results (prevents deletion)."""
    result_count = (
        session.query(func.count(Result.id))
        .join(Tournament, Result.tournament_id == Tournament.id)
        .filter(Tournament.event_id == event_id)
        .scalar()
    )
    if result_count and result_count > 0:
        return "Cannot delete event with tournament results"
    return None


def _delete_event_cascade(session: Session, event_id: int) -> None:
    """Delete all data associated with an event before deleting the event itself."""
    # Get all poll IDs for this event
    poll_ids_query = select(Poll.id).where(Poll.event_id == event_id)
    poll_ids = list(session.execute(poll_ids_query).scalars().all())

    # Delete poll votes and options for all polls
    if poll_ids:
        bulk_delete(session, PollVote, [PollVote.poll_id.in_(poll_ids)])
        bulk_delete(session, PollOption, [PollOption.poll_id.in_(poll_ids)])

    # Delete polls
    bulk_delete(session, Poll, [Poll.event_id == event_id])

    # Delete tournaments
    bulk_delete(session, Tournament, [Tournament.event_id == event_id])


@router.post("/admin/events/{event_id}/delete")
async def delete_event_post(request: Request, event_id: int) -> Response:
    """Delete an event via POST (for form submissions)."""
    return delete_entity(
        request,
        event_id,
        Event,
        redirect_url="/admin/events",
        success_message="Event deleted successfully",
        error_message="Failed to delete event",
        validation_check=_check_event_has_results,
        pre_delete_hook=_delete_event_cascade,
    )


@router.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int) -> Response:
    """Delete an event and its associated data."""
    return delete_entity(
        request,
        event_id,
        Event,
        success_message="Event deleted successfully",
        error_message="Failed to delete event",
        validation_check=_check_event_has_results,
        pre_delete_hook=_delete_event_cascade,
    )
