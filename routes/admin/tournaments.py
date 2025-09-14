"""Admin tournaments routes - tournament management."""

import json
from fastapi import APIRouter, Request, Form
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
            "total_participants": t[9] + t[10],
        }
        for t in tournaments
    ]

    return templates.TemplateResponse(
        "admin/tournaments.html",
        {"request": request, "user": user, "tournaments": tournaments_data},
    )


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


@router.get("/admin/tournaments/{tournament_id}/enter-results")
async def enter_results_form(request: Request, tournament_id: int):
    """Show results entry form for a tournament."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    # Get tournament details
    tournament_data = db("""
        SELECT t.id, t.name, e.date, t.lake_name, t.ramp_name,
               t.fish_limit, t.entry_fee, t.complete
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        WHERE t.id = :tournament_id
    """, {"tournament_id": tournament_id})

    if not tournament_data:
        return RedirectResponse("/admin/tournaments?error=Tournament not found", status_code=302)

    tournament = {
        "id": tournament_data[0][0],
        "name": tournament_data[0][1],
        "date": tournament_data[0][2],
        "lake_name": tournament_data[0][3],
        "ramp_name": tournament_data[0][4],
        "fish_limit": tournament_data[0][5],
        "entry_fee": tournament_data[0][6],
        "complete": bool(tournament_data[0][7])
    }

    # Get all anglers for dropdown
    anglers = db("SELECT id, name FROM anglers ORDER BY name")
    anglers_json = json.dumps([{"id": a[0], "name": a[1]} for a in anglers])

    return templates.TemplateResponse(
        "admin/enter_results.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "anglers_json": anglers_json
        }
    )


@router.post("/admin/tournaments/{tournament_id}/enter-results")
async def save_results(request: Request, tournament_id: int):
    """Save tournament results."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()

        # Parse team results from form data
        teams = {}

        # Group form data by team number
        for key, value in form.items():
            if '_' in key:
                parts = key.split('_')
                if len(parts) >= 3:
                    angler = parts[0]  # angler1 or angler2
                    field = parts[1]   # id, fish, weight, etc
                    team_num = parts[2] # team number

                    if team_num not in teams:
                        teams[team_num] = {}
                    if angler not in teams[team_num]:
                        teams[team_num][angler] = {}

                    teams[team_num][angler][field] = value

        # Process each team
        for team_num, team_data in teams.items():
            if 'angler1' in team_data and 'angler2' in team_data:
                angler1 = team_data['angler1']
                angler2 = team_data['angler2']

                # Skip if required fields are missing
                if not angler1.get('id') or not angler2.get('id'):
                    continue

                # Insert individual results for both anglers
                for angler_key, angler in [('angler1', angler1), ('angler2', angler2)]:
                    db("""
                        INSERT INTO results (
                            tournament_id, angler_id, num_fish, total_weight,
                            big_bass_weight, dead_fish_penalty, disqualified
                        ) VALUES (
                            :tournament_id, :angler_id, :num_fish, :total_weight,
                            :big_bass_weight, :dead_fish_penalty, :disqualified
                        )
                    """, {
                        "tournament_id": tournament_id,
                        "angler_id": int(angler['id']),
                        "num_fish": int(angler.get('fish', 0)),
                        "total_weight": float(angler.get('weight', 0)),
                        "big_bass_weight": float(angler.get('bass', 0)),
                        "dead_fish_penalty": float(angler.get('penalty', 0)),
                        "disqualified": bool(angler.get('disqualified', False))
                    })

                # Calculate team total weight
                team_weight = (float(angler1.get('weight', 0)) - float(angler1.get('penalty', 0)) +
                              float(angler2.get('weight', 0)) - float(angler2.get('penalty', 0)))

                # Insert team result
                db("""
                    INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight)
                    VALUES (:tournament_id, :angler1_id, :angler2_id, :total_weight)
                """, {
                    "tournament_id": tournament_id,
                    "angler1_id": int(angler1['id']),
                    "angler2_id": int(angler2['id']),
                    "total_weight": team_weight
                })

        # Mark tournament as complete
        db("UPDATE tournaments SET complete = 1 WHERE id = :tournament_id",
           {"tournament_id": tournament_id})

        return RedirectResponse(f"/tournaments/{tournament_id}?success=Results saved successfully", status_code=302)

    except Exception as e:
        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results?error=Failed to save results: {str(e)}",
            status_code=302
        )
