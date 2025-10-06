from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from core.helpers.auth import require_admin
from routes.dependencies import db, engine

router = APIRouter()


@router.delete("/admin/events/{event_id}")
async def delete_event(request: Request, event_id: int):
    """Delete an event and its associated data."""
    _user = require_admin(request)
    try:
        # Check if event has results
        has_results = db(
            """SELECT COUNT(*)
               FROM results r
               JOIN tournaments t ON r.tournament_id = t.id
               WHERE t.event_id = :event_id""",
            {"event_id": event_id},
        )

        if has_results and has_results[0][0] > 0:
            return JSONResponse(
                {"error": "Cannot delete event with tournament results"}, status_code=400
            )

        # Delete event and cascading data
        with engine.begin() as conn:
            # Delete poll votes
            conn.execute(
                text(
                    "DELETE FROM poll_votes WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )

            # Delete poll options
            conn.execute(
                text(
                    "DELETE FROM poll_options WHERE poll_id IN (SELECT id FROM polls WHERE event_id = :event_id)"
                ),
                {"event_id": event_id},
            )

            # Delete polls
            conn.execute(
                text("DELETE FROM polls WHERE event_id = :event_id"), {"event_id": event_id}
            )

            # Delete event (tournaments cascade automatically)
            conn.execute(text("DELETE FROM events WHERE id = :id"), {"id": event_id})
            # Auto-commits on context exit - no explicit commit needed

        return JSONResponse({"success": True}, status_code=200)

    except Exception as e:
        return JSONResponse({"error": f"Database error: {str(e)}"}, status_code=500)
