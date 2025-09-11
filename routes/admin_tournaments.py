"""Admin tournaments routes - tournament management."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from routes.dependencies import admin, db, templates

router = APIRouter()


@router.get("/admin/tournaments")
async def admin_tournaments_list(request: Request):
    """Admin tournaments list page."""
    if isinstance(user := admin(request), RedirectResponse):
        return user
    
    # Get all tournaments with event and result data
    tournaments = db("""
        SELECT t.id, t.event_id, e.date, e.name, t.lake_name, t.ramp_name, 
               t.entry_fee, t.complete, t.fish_limit,
               COUNT(DISTINCT r.id) as result_count,
               COUNT(DISTINCT tr.id) as team_result_count
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN results r ON t.id = r.tournament_id
        LEFT JOIN team_results tr ON t.id = tr.tournament_id
        GROUP BY t.id, t.event_id, e.date, e.name, t.lake_name, t.ramp_name, 
                 t.entry_fee, t.complete, t.fish_limit
        ORDER BY e.date DESC
    """)
    
    tournaments_data = [
        {
            "id": t[0],
            "event_id": t[1], 
            "date": t[2],
            "name": t[3],
            "lake_name": t[4],
            "ramp_name": t[5],
            "entry_fee": t[6],
            "complete": bool(t[7]),
            "fish_limit": t[8],
            "result_count": t[9],
            "team_result_count": t[10],
            "total_participants": t[9] + t[10]
        }
        for t in tournaments
    ]
    
    return templates.TemplateResponse("admin/tournaments.html", {
        "request": request, 
        "user": user, 
        "tournaments": tournaments_data
    })


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
