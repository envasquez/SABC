from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select

from core.db_schema import Event, Poll, PollOption, PollVote, Result, Tournament, get_session
from core.helpers.auth import require_admin

router = APIRouter()


@router.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int):
    """Delete an event and its associated data."""
    _user = require_admin(request)
    try:
        with get_session() as session:
            # Check if event has results
            result_count = (
                session.query(func.count(Result.id))
                .join(Tournament, Result.tournament_id == Tournament.id)
                .filter(Tournament.event_id == event_id)
                .scalar()
            )

            if result_count and result_count > 0:
                return JSONResponse(
                    {"error": "Cannot delete event with tournament results"}, status_code=400
                )

            # Get all poll IDs for this event
            poll_ids_query = select(Poll.id).where(Poll.event_id == event_id)
            poll_ids = session.execute(poll_ids_query).scalars().all()

            # Delete poll votes
            if poll_ids:
                session.query(PollVote).filter(PollVote.poll_id.in_(poll_ids)).delete(
                    synchronize_session=False
                )

            # Delete poll options
            if poll_ids:
                session.query(PollOption).filter(PollOption.poll_id.in_(poll_ids)).delete(
                    synchronize_session=False
                )

            # Delete polls
            session.query(Poll).filter(Poll.event_id == event_id).delete(synchronize_session=False)

            # Delete event (tournaments cascade automatically)
            event = session.query(Event).filter(Event.id == event_id).first()
            if event:
                session.delete(event)

        return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
