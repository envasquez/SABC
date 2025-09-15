"""Admin tournaments routes - tournament management."""

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, RedirectResponse

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

    # Check if we're editing an existing result
    edit_result_id = request.query_params.get("edit_result")
    edit_team_result_id = request.query_params.get("edit_team_result")

    # Get tournament details
    tournament_data = db(
        """
        SELECT t.id, t.name, e.date, t.lake_name, t.ramp_name,
               t.fish_limit, t.entry_fee, t.complete
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        WHERE t.id = :tournament_id
    """,
        {"tournament_id": tournament_id},
    )

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
        "complete": bool(tournament_data[0][7]),
    }

    # Get anglers who already have results in this tournament
    existing_angler_ids = db(
        "SELECT DISTINCT angler_id FROM results WHERE tournament_id = :tournament_id",
        {"tournament_id": tournament_id},
    )
    existing_ids = {str(row[0]) for row in existing_angler_ids}

    # Get all anglers for dropdown
    anglers = db("SELECT id, name FROM anglers ORDER BY name")
    anglers_json = json.dumps([{"id": a[0], "name": a[1]} for a in anglers])
    existing_ids_json = json.dumps(list(existing_ids))

    # Get existing result data if editing
    edit_data = None
    if edit_result_id:
        result_data = db(
            """
            SELECT r.id, r.angler_id, a.name, r.num_fish, r.total_weight,
                   r.big_bass_weight, r.dead_fish_penalty, r.disqualified, r.buy_in
            FROM results r
            JOIN anglers a ON r.angler_id = a.id
            WHERE r.id = :result_id AND r.tournament_id = :tournament_id
            """,
            {"result_id": edit_result_id, "tournament_id": tournament_id},
        )
        if result_data:
            result = result_data[0]
            edit_data = {
                "type": "individual",
                "result_id": result[0],
                "angler_id": result[1],
                "angler_name": result[2],
                "num_fish": result[3],
                "total_weight": result[4],
                "big_bass_weight": result[5],
                "dead_fish_penalty": result[6],
                "disqualified": bool(result[7]),
                "buy_in": bool(result[8]),
            }

    elif edit_team_result_id:
        team_data = db(
            """
            SELECT tr.id, tr.angler1_id, tr.angler2_id, a1.name, a2.name, tr.total_weight
            FROM team_results tr
            JOIN anglers a1 ON tr.angler1_id = a1.id
            LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
            WHERE tr.id = :team_result_id AND tr.tournament_id = :tournament_id
            """,
            {"team_result_id": edit_team_result_id, "tournament_id": tournament_id},
        )
        if team_data:
            team = team_data[0]
            # Get individual results for the team members
            angler1_result = db(
                """
                SELECT num_fish, total_weight, big_bass_weight, dead_fish_penalty, disqualified, buy_in
                FROM results WHERE angler_id = :angler1_id AND tournament_id = :tournament_id
                """,
                {"angler1_id": team[1], "tournament_id": tournament_id},
            )
            angler2_result = None
            if team[2]:  # If there's a second angler
                angler2_result = db(
                    """
                    SELECT num_fish, total_weight, big_bass_weight, dead_fish_penalty, disqualified, buy_in
                    FROM results WHERE angler_id = :angler2_id AND tournament_id = :tournament_id
                    """,
                    {"angler2_id": team[2], "tournament_id": tournament_id},
                )

            angler1_data = list(angler1_result[0]) if angler1_result else [0, 0, 0, 0, False, False]
            angler2_data = list(angler2_result[0]) if angler2_result else [0, 0, 0, 0, False, False]

            edit_data = {
                "type": "team",
                "team_result_id": team[0],
                "angler1_id": team[1],
                "angler2_id": team[2],
                "angler1_name": team[3],
                "angler2_name": team[4],
                "total_weight": team[5],
                "angler1_result": angler1_data,
                "angler2_result": angler2_data,
            }

    return templates.TemplateResponse(
        "admin/enter_results.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "anglers_json": anglers_json,
            "existing_angler_ids_json": existing_ids_json,
            "edit_data": edit_data,
        },
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
            if "_" in key:
                parts = key.split("_")
                if len(parts) >= 3:
                    angler = parts[0]  # angler1 or angler2
                    field = parts[1]  # id, fish, weight, etc
                    team_num = parts[2]  # team number

                    if team_num not in teams:
                        teams[team_num] = {}
                    if angler not in teams[team_num]:
                        teams[team_num][angler] = {}

                    teams[team_num][angler][field] = value

        # Process each team
        for team_num, team_data in teams.items():
            if "angler1" in team_data:
                angler1 = team_data["angler1"]
                angler2 = team_data.get("angler2", {})

                # Skip if angler 1 is missing (required)
                if not angler1.get("id"):
                    continue

                # Insert individual results for anglers
                anglers_to_process = [("angler1", angler1)]
                if angler2.get("id"):  # Only process angler2 if they have an ID
                    anglers_to_process.append(("angler2", angler2))

                for angler_key, angler in anglers_to_process:
                    db(
                        """
                        INSERT INTO results (
                            tournament_id, angler_id, num_fish, total_weight,
                            big_bass_weight, dead_fish_penalty, disqualified, buy_in
                        ) VALUES (
                            :tournament_id, :angler_id, :num_fish, :total_weight,
                            :big_bass_weight, :dead_fish_penalty, :disqualified, :buy_in
                        )
                    """,
                        {
                            "tournament_id": tournament_id,
                            "angler_id": int(angler["id"]),
                            "num_fish": int(angler.get("fish", 0)),
                            "total_weight": float(angler.get("weight", 0)),
                            "big_bass_weight": float(angler.get("bass", 0)),
                            "dead_fish_penalty": float(angler.get("penalty", 0)),
                            "disqualified": bool(angler.get("disqualified", False)),
                            "buy_in": bool(angler.get("buyIn", False)),
                        },
                    )

                # Create team result for both 2-person teams and solo anglers
                if angler2.get("id"):
                    # Two-person team
                    team_weight = (
                        float(angler1.get("weight", 0))
                        - float(angler1.get("penalty", 0))
                        + float(angler2.get("weight", 0))
                        - float(angler2.get("penalty", 0))
                    )

                    # Insert team result with both anglers
                    db(
                        """
                        INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight)
                        VALUES (:tournament_id, :angler1_id, :angler2_id, :total_weight)
                    """,
                        {
                            "tournament_id": tournament_id,
                            "angler1_id": int(angler1["id"]),
                            "angler2_id": int(angler2["id"]),
                            "total_weight": team_weight,
                        },
                    )
                else:
                    # Solo angler
                    team_weight = float(angler1.get("weight", 0)) - float(angler1.get("penalty", 0))

                    # Insert team result with only angler1 (angler2_id = NULL for solo)
                    db(
                        """
                        INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight)
                        VALUES (:tournament_id, :angler1_id, NULL, :total_weight)
                    """,
                        {
                            "tournament_id": tournament_id,
                            "angler1_id": int(angler1["id"]),
                            "total_weight": team_weight,
                        },
                    )

        # Mark tournament as complete
        db(
            "UPDATE tournaments SET complete = 1 WHERE id = :tournament_id",
            {"tournament_id": tournament_id},
        )

        return RedirectResponse(
            f"/tournaments/{tournament_id}?success=Results saved successfully", status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results?error=Failed to save results: {str(e)}",
            status_code=302,
        )


@router.delete("/admin/results/{result_id}")
async def delete_individual_result(request: Request, result_id: int):
    """Delete an individual result."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Get the result to verify it exists
        result = db(
            "SELECT id, tournament_id FROM results WHERE id = :result_id",
            {"result_id": result_id},
        )

        if not result:
            return JSONResponse({"error": "Result not found"}, status_code=404)

        # Delete the result
        db("DELETE FROM results WHERE id = :result_id", {"result_id": result_id})

        return JSONResponse({"success": True, "message": "Individual result deleted successfully"})

    except Exception as e:
        return JSONResponse({"error": f"Failed to delete result: {str(e)}"}, status_code=500)


@router.delete("/admin/team-results/{team_result_id}")
async def delete_team_result(request: Request, team_result_id: int):
    """Delete a team result and associated individual results."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        # Get the team result with angler IDs to verify it exists and get associated individual results
        team_result = db(
            "SELECT id, tournament_id, angler1_id, angler2_id FROM team_results WHERE id = :team_result_id",
            {"team_result_id": team_result_id},
        )

        if not team_result:
            return JSONResponse({"error": "Team result not found"}, status_code=404)

        tournament_id = team_result[0][1]
        angler1_id = team_result[0][2]
        angler2_id = team_result[0][3]

        # Delete the individual results for both team members in this tournament
        db(
            """DELETE FROM results
               WHERE tournament_id = :tournament_id
               AND angler_id IN (:angler1_id, :angler2_id)""",
            {
                "tournament_id": tournament_id,
                "angler1_id": angler1_id,
                "angler2_id": angler2_id,
            },
        )

        # Delete the team result
        db(
            "DELETE FROM team_results WHERE id = :team_result_id",
            {"team_result_id": team_result_id},
        )

        return JSONResponse(
            {
                "success": True,
                "message": "Team result and associated individual results deleted successfully",
            }
        )

    except Exception as e:
        return JSONResponse({"error": f"Failed to delete team result: {str(e)}"}, status_code=500)


@router.post("/admin/results/{result_id}/edit")
async def edit_individual_result(request: Request, result_id: int):
    """Edit an individual tournament result."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()

        # Get the tournament_id for redirect
        result_data = db(
            "SELECT tournament_id FROM results WHERE id = :result_id", {"result_id": result_id}
        )
        if not result_data:
            return RedirectResponse("/admin/tournaments?error=Result not found", status_code=302)

        tournament_id = result_data[0][0]

        # Update the individual result
        db(
            """
            UPDATE results SET
                num_fish = :num_fish,
                total_weight = :total_weight,
                big_bass_weight = :big_bass_weight,
                dead_fish_penalty = :dead_fish_penalty,
                disqualified = :disqualified,
                buy_in = :buy_in
            WHERE id = :result_id
        """,
            {
                "result_id": result_id,
                "num_fish": int(form.get("num_fish", 0)),
                "total_weight": float(form.get("total_weight", 0)),
                "big_bass_weight": float(form.get("big_bass_weight", 0)),
                "dead_fish_penalty": float(form.get("dead_fish_penalty", 0)),
                "disqualified": bool(form.get("disqualified")),
                "buy_in": bool(form.get("buy_in")),
            },
        )

        # Update any related team results
        # Get team results that include this angler
        team_results = db(
            """
            SELECT tr.id, tr.angler1_id, tr.angler2_id
            FROM team_results tr
            JOIN results r ON (r.angler_id = tr.angler1_id OR r.angler_id = tr.angler2_id)
            WHERE r.id = :result_id
        """,
            {"result_id": result_id},
        )

        for team_result in team_results:
            team_id, angler1_id, angler2_id = team_result

            # Recalculate team total weight
            angler1_result = db(
                "SELECT total_weight, dead_fish_penalty FROM results WHERE angler_id = :angler_id AND tournament_id = :tournament_id",
                {"angler_id": angler1_id, "tournament_id": tournament_id},
            )[0]

            total_weight = angler1_result[0] - angler1_result[1]

            if angler2_id:  # Only add angler2 if they exist (not solo)
                angler2_result = db(
                    "SELECT total_weight, dead_fish_penalty FROM results WHERE angler_id = :angler_id AND tournament_id = :tournament_id",
                    {"angler_id": angler2_id, "tournament_id": tournament_id},
                )[0]
                total_weight += angler2_result[0] - angler2_result[1]

            db(
                "UPDATE team_results SET total_weight = :total_weight WHERE id = :team_id",
                {"total_weight": total_weight, "team_id": team_id},
            )

        return RedirectResponse(
            f"/tournaments/{tournament_id}?success=Result updated successfully", status_code=302
        )

    except Exception as e:
        return RedirectResponse(
            f"/tournaments/{tournament_id}?error=Failed to update result: {str(e)}", status_code=302
        )


@router.post("/admin/team-results/{team_result_id}/edit")
async def edit_team_result(request: Request, team_result_id: int):
    """Edit a team tournament result."""
    if isinstance(user := admin(request), RedirectResponse):
        return user

    try:
        form = await request.form()

        # Get the tournament_id for redirect
        team_data = db(
            "SELECT tournament_id FROM team_results WHERE id = :team_result_id",
            {"team_result_id": team_result_id},
        )
        if not team_data:
            return RedirectResponse(
                "/admin/tournaments?error=Team result not found", status_code=302
            )

        tournament_id = team_data[0][0]

        # Update the team result
        db(
            """
            UPDATE team_results SET
                total_weight = :total_weight
            WHERE id = :team_result_id
        """,
            {"team_result_id": team_result_id, "total_weight": float(form.get("total_weight", 0))},
        )

        return RedirectResponse(
            f"/tournaments/{tournament_id}?success=Team result updated successfully",
            status_code=302,
        )

    except Exception as e:
        return RedirectResponse(
            f"/tournaments/{tournament_id}?error=Failed to update team result: {str(e)}",
            status_code=302,
        )
