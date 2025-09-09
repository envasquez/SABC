"""Admin tournaments routes - tournament management."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from routes.dependencies import admin, db

router = APIRouter()


@router.post("/admin/tournaments/create")
async def create_tournament(request: Request):
    """Create a new tournament."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()
        event_id_raw = form.get("event_id")
        event_id = int(event_id_raw) if isinstance(event_id_raw, str) else 0
        name = form.get("name")
        lake_name = form.get("lake_name", "")
        entry_fee_raw = form.get("entry_fee", "25.0")
        entry_fee = float(entry_fee_raw) if isinstance(entry_fee_raw, str) else 25.0

        # Insert tournament
        db(
            """
            INSERT INTO tournaments (event_id, name, lake_name, entry_fee, complete)
            VALUES (:event_id, :name, :lake_name, :entry_fee, 0)
        """,
            {"event_id": event_id, "name": name, "lake_name": lake_name, "entry_fee": entry_fee},
        )

        return RedirectResponse("/admin/events?success=Tournament created", status_code=302)
    except Exception as e:
        return RedirectResponse(
            f"/admin/events?error=Failed to create tournament: {str(e)}", status_code=302
        )
