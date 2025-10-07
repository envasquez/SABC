from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.db_schema import Event, Poll, Tournament, get_session
from core.helpers.auth import require_admin

router = APIRouter()


@router.get("/admin/events/{event_id}/info")
async def get_event_info(request: Request, event_id: int):
    """Get event information as JSON for editing forms."""
    _user = require_admin(request)
    try:
        with get_session() as session:
            # Query event with left joins to tournament and poll
            result = (
                session.query(Event, Tournament, Poll)
                .outerjoin(Tournament, Event.id == Tournament.event_id)
                .outerjoin(Poll, Event.id == Poll.event_id)
                .filter(Event.id == event_id)
                .first()
            )

            if result:
                event, tournament, poll = result
                # Prefer event data, but fall back to tournament data if event fields are null
                lake_display_name = event.lake_name or (tournament.lake_name if tournament else "") or ""
                ramp_name = event.ramp_name or (tournament.ramp_name if tournament else "") or ""

                return JSONResponse(
                    {
                        "id": event.id,
                        "date": str(event.date) if event.date else "",
                        "name": event.name,
                        "description": event.description or "",
                        "event_type": event.event_type,
                        "start_time": event.start_time.strftime("%H:%M")
                        if event.start_time is not None
                        else "",
                        "weigh_in_time": event.weigh_in_time.strftime("%H:%M")
                        if event.weigh_in_time is not None
                        else "",
                        "lake_name": lake_display_name,
                        "ramp_name": ramp_name,
                        "entry_fee": float(event.entry_fee)
                        if event.entry_fee is not None
                        else None,
                        "fish_limit": tournament.fish_limit if tournament else None,
                        "holiday_name": event.holiday_name or "",
                        "poll_closes_at": poll.closes_at.isoformat()
                        if poll and poll.closes_at is not None
                        else "",
                        "poll_starts_at": poll.starts_at.isoformat()
                        if poll and poll.starts_at is not None
                        else "",
                        "poll_id": poll.id if poll else None,
                        "poll_closed": bool(poll.closed)
                        if poll and poll.closed is not None
                        else None,
                        "tournament_id": tournament.id if tournament else None,
                        "aoy_points": bool(tournament.aoy_points)
                        if tournament and tournament.aoy_points is not None
                        else True,
                    }
                )
            else:
                return JSONResponse({"error": "Event not found"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": f"Failed to get event info: {str(e)}"}, status_code=500)
