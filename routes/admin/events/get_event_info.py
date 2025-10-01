from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from core.helpers.auth import require_admin
from routes.dependencies import db

router = APIRouter()


@router.get("/admin/events/{event_id}/info")
async def get_event_info(request: Request, event_id: int):
    """Get event information as JSON for editing forms."""
    _user = require_admin(request)
    try:
        event_info = db(
            """SELECT e.id, e.date, e.name, e.description, e.event_type,
               e.start_time, e.weigh_in_time, e.lake_name, e.ramp_name, e.entry_fee,
               t.fish_limit, e.holiday_name, p.closes_at, p.starts_at, p.id, p.closed, t.id, t.aoy_points
               FROM events e
               LEFT JOIN tournaments t ON e.id = t.event_id
               LEFT JOIN polls p ON e.id = p.event_id
               WHERE e.id = :event_id""",
            {"event_id": event_id},
        )

        if event_info:
            event = event_info[0]
            lake_display_name = event[7] or ""

            return JSONResponse(
                {
                    "id": event[0],
                    "date": str(event[1]) if event[1] else "",
                    "name": event[2],
                    "description": event[3] or "",
                    "event_type": event[4],
                    "start_time": event[5].strftime("%H:%M") if event[5] is not None else "",
                    "weigh_in_time": event[6].strftime("%H:%M") if event[6] is not None else "",
                    "lake_name": lake_display_name,
                    "ramp_name": event[8] or "",
                    "entry_fee": float(event[9]) if event[9] is not None else None,
                    "fish_limit": event[10],
                    "holiday_name": event[11] or "",
                    "poll_closes_at": event[12].isoformat() if event[12] is not None else "",
                    "poll_starts_at": event[13].isoformat() if event[13] is not None else "",
                    "poll_id": event[14],
                    "poll_closed": bool(event[15]) if event[15] is not None else None,
                    "tournament_id": event[16],
                    "aoy_points": bool(event[17]) if event[17] is not None else True,
                }
            )
        else:
            return JSONResponse({"error": "Event not found"}, status_code=404)

    except Exception as e:
        return JSONResponse({"error": f"Failed to get event info: {str(e)}"}, status_code=500)
