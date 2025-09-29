"""Tournament admin routes."""

from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Connection

from core.deps import get_admin_or_redirect, get_db, render
from core.query_service import QueryService

# Schemas imported but not used yet - will be implemented in next iteration

router = APIRouter()


@router.get("/admin/tournaments")
async def admin_tournaments_list(
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    qs = QueryService(conn)
    tournaments = qs.fetch_all("""
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

    for t in tournaments:
        t["total_participants"] = t["result_count"] + t["team_result_count"]

    return render("admin/tournaments.html", request, user=user, tournaments=tournaments)


@router.get("/admin/tournaments/{tournament_id}/enter-results")
async def enter_results_page(
    tournament_id: int,
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    qs = QueryService(conn)
    tournament = qs.get_tournament_by_id(tournament_id)
    if not tournament:
        return RedirectResponse("/admin/tournaments", status_code=303)

    # Get all anglers and existing results
    anglers = qs.get_all_anglers()
    results = qs.get_tournament_results(tournament_id)
    team_results = qs.get_team_results(tournament_id)

    # Create lookup for existing results
    results_by_angler = {r["angler_id"]: r for r in results}
    teams_set = {(tr["angler1_id"], tr["angler2_id"]) for tr in team_results}

    # Handle team result editing
    edit_team_result_id = request.query_params.get("edit_team_result")
    edit_team_result_data = None
    if edit_team_result_id:
        edit_team_result_data = qs.fetch_one(
            """SELECT tr.*, a1.name as angler1_name, a2.name as angler2_name
               FROM team_results tr
               JOIN anglers a1 ON tr.angler1_id = a1.id
               JOIN anglers a2 ON tr.angler2_id = a2.id
               WHERE tr.id = :id""",
            {"id": int(edit_team_result_id)},
        )
        # Convert all Decimal fields to float for JSON serialization
        if edit_team_result_data:
            edit_team_result_data = dict(edit_team_result_data)
            from decimal import Decimal

            for key, value in edit_team_result_data.items():
                if isinstance(value, Decimal):
                    edit_team_result_data[key] = float(value)

    # Create JSON data for JavaScript
    import json

    anglers_json = json.dumps([{"id": a["id"], "name": a["name"]} for a in anglers])
    existing_angler_ids = list(results_by_angler.keys())
    existing_angler_ids_json = json.dumps(existing_angler_ids)

    return render(
        "admin/enter_results.html",
        request,
        user=user,
        tournament=tournament,
        anglers=anglers,
        anglers_json=anglers_json,
        existing_angler_ids_json=existing_angler_ids_json,
        results_by_angler=results_by_angler,
        team_results=team_results,
        teams_set=teams_set,
        edit_result_id=request.query_params.get("edit_result_id"),
        edit_team_result=edit_team_result_id,
        edit_team_result_data=edit_team_result_data,
    )


@router.post("/admin/tournaments/{tournament_id}/results")
async def save_result(
    tournament_id: int,
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    qs = QueryService(conn)

    # Parse form data
    angler_id = int(form.get("angler_id"))
    num_fish = int(form.get("num_fish", 0))
    total_weight = Decimal(form.get("total_weight", "0"))
    big_bass_weight = Decimal(form.get("big_bass_weight", "0"))
    dead_fish = int(form.get("dead_fish", 0))
    disqualified = form.get("disqualified") == "on"
    buy_in = form.get("buy_in") == "on"

    # Calculate penalty
    dead_fish_penalty = Decimal(dead_fish * 0.25)

    # Check for existing result
    existing = qs.fetch_one(
        "SELECT id FROM results WHERE tournament_id = :tid AND angler_id = :aid",
        {"tid": tournament_id, "aid": angler_id},
    )

    if existing:
        # Update existing result
        qs.execute(
            """UPDATE results SET num_fish = :num_fish, total_weight = :total_weight,
               big_bass_weight = :big_bass_weight, dead_fish_penalty = :penalty,
               disqualified = :disqualified, buy_in = :buy_in
               WHERE id = :id""",
            {
                "num_fish": num_fish,
                "total_weight": total_weight,
                "big_bass_weight": big_bass_weight,
                "penalty": dead_fish_penalty,
                "disqualified": disqualified,
                "buy_in": buy_in,
                "id": existing["id"],
            },
        )
    else:
        # Insert new result
        qs.execute(
            """INSERT INTO results
               (tournament_id, angler_id, num_fish, total_weight, big_bass_weight,
                dead_fish_penalty, disqualified, buy_in)
               VALUES (:tid, :aid, :num_fish, :total_weight, :big_bass_weight,
                       :penalty, :disqualified, :buy_in)""",
            {
                "tid": tournament_id,
                "aid": angler_id,
                "num_fish": num_fish,
                "total_weight": total_weight,
                "big_bass_weight": big_bass_weight,
                "penalty": dead_fish_penalty,
                "disqualified": disqualified,
                "buy_in": buy_in,
            },
        )

    return RedirectResponse(f"/admin/tournaments/{tournament_id}/enter-results", status_code=303)


@router.post("/admin/tournaments/{tournament_id}/team-results")
async def save_team_result(
    tournament_id: int,
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    qs = QueryService(conn)

    # Parse form data
    angler1_id = int(form.get("angler1_id"))
    angler2_id = int(form.get("angler2_id"))
    total_weight = Decimal(form.get("total_weight", "0"))
    team_result_id = form.get("team_result_id")  # For editing existing team

    if angler1_id == angler2_id:
        return JSONResponse({"error": "Team members must be different"}, status_code=400)

    # Ensure consistent ordering
    if angler1_id > angler2_id:
        angler1_id, angler2_id = angler2_id, angler1_id

    if team_result_id:
        # Update existing team result by ID
        qs.execute(
            """UPDATE team_results
               SET angler1_id = :a1, angler2_id = :a2, total_weight = :weight
               WHERE id = :id""",
            {"a1": angler1_id, "a2": angler2_id, "weight": total_weight, "id": int(team_result_id)},
        )
    else:
        # Check for existing team result
        existing = qs.fetch_one(
            """SELECT id FROM team_results
               WHERE tournament_id = :tid AND angler1_id = :a1 AND angler2_id = :a2""",
            {"tid": tournament_id, "a1": angler1_id, "a2": angler2_id},
        )

        if existing:
            # Update existing
            qs.execute(
                "UPDATE team_results SET total_weight = :weight WHERE id = :id",
                {"weight": total_weight, "id": existing["id"]},
            )
        else:
            # Insert new
            qs.execute(
                """INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight)
                   VALUES (:tid, :a1, :a2, :weight)""",
                {"tid": tournament_id, "a1": angler1_id, "a2": angler2_id, "weight": total_weight},
            )

    return RedirectResponse(f"/admin/tournaments/{tournament_id}/enter-results", status_code=303)


@router.post("/admin/tournaments/{tournament_id}/enter-results")
async def save_multiple_results(
    tournament_id: int,
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    qs = QueryService(conn)

    # Process all teams from the form
    team_num = 1
    saved_count = 0

    while f"angler1_id_{team_num}" in form:
        angler1_id = form.get(f"angler1_id_{team_num}")
        angler2_id = form.get(f"angler2_id_{team_num}")

        # Convert to int if present
        if angler1_id:
            angler1_id = int(angler1_id)
        if angler2_id:
            angler2_id = int(angler2_id)

        if angler1_id:
            # Process angler1 results
            angler1_fish = int(form.get(f"angler1_fish_{team_num}", 0))
            angler1_weight = Decimal(form.get(f"angler1_weight_{team_num}", "0"))
            angler1_big_bass = Decimal(form.get(f"angler1_big_bass_{team_num}", "0"))
            angler1_dead_penalty = Decimal(form.get(f"angler1_dead_penalty_{team_num}", "0"))
            angler1_disqualified = form.get(f"angler1_disqualified_{team_num}") == "1"
            angler1_buy_in = form.get(f"angler1_buyIn_{team_num}") == "1"

            # Save angler1 result
            existing = qs.fetch_one(
                "SELECT id FROM results WHERE tournament_id = :tid AND angler_id = :aid",
                {"tid": tournament_id, "aid": angler1_id},
            )

            if existing:
                qs.execute(
                    """UPDATE results SET num_fish = :fish, total_weight = :weight,
                       big_bass_weight = :bass, dead_fish_penalty = :penalty,
                       disqualified = :dq, buy_in = :buy
                       WHERE id = :id""",
                    {
                        "fish": angler1_fish,
                        "weight": angler1_weight,
                        "bass": angler1_big_bass,
                        "penalty": angler1_dead_penalty,
                        "dq": angler1_disqualified,
                        "buy": angler1_buy_in,
                        "id": existing["id"],
                    },
                )
            else:
                qs.execute(
                    """INSERT INTO results (tournament_id, angler_id, num_fish, total_weight,
                       big_bass_weight, dead_fish_penalty, disqualified, buy_in)
                       VALUES (:tid, :aid, :fish, :weight, :bass, :penalty, :dq, :buy)""",
                    {
                        "tid": tournament_id,
                        "aid": angler1_id,
                        "fish": angler1_fish,
                        "weight": angler1_weight,
                        "bass": angler1_big_bass,
                        "penalty": angler1_dead_penalty,
                        "dq": angler1_disqualified,
                        "buy": angler1_buy_in,
                    },
                )
            saved_count += 1

        if angler2_id:
            # Process angler2 results
            angler2_fish = int(form.get(f"angler2_fish_{team_num}", 0))
            angler2_weight = Decimal(form.get(f"angler2_weight_{team_num}", "0"))
            angler2_big_bass = Decimal(form.get(f"angler2_big_bass_{team_num}", "0"))
            angler2_dead_penalty = Decimal(form.get(f"angler2_dead_penalty_{team_num}", "0"))
            angler2_disqualified = form.get(f"angler2_disqualified_{team_num}") == "1"
            angler2_buy_in = form.get(f"angler2_buyIn_{team_num}") == "1"

            # Save angler2 result
            existing = qs.fetch_one(
                "SELECT id FROM results WHERE tournament_id = :tid AND angler_id = :aid",
                {"tid": tournament_id, "aid": angler2_id},
            )

            if existing:
                qs.execute(
                    """UPDATE results SET num_fish = :fish, total_weight = :weight,
                       big_bass_weight = :bass, dead_fish_penalty = :penalty,
                       disqualified = :dq, buy_in = :buy
                       WHERE id = :id""",
                    {
                        "fish": angler2_fish,
                        "weight": angler2_weight,
                        "bass": angler2_big_bass,
                        "penalty": angler2_dead_penalty,
                        "dq": angler2_disqualified,
                        "buy": angler2_buy_in,
                        "id": existing["id"],
                    },
                )
            else:
                qs.execute(
                    """INSERT INTO results (tournament_id, angler_id, num_fish, total_weight,
                       big_bass_weight, dead_fish_penalty, disqualified, buy_in)
                       VALUES (:tid, :aid, :fish, :weight, :bass, :penalty, :dq, :buy)""",
                    {
                        "tid": tournament_id,
                        "aid": angler2_id,
                        "fish": angler2_fish,
                        "weight": angler2_weight,
                        "bass": angler2_big_bass,
                        "penalty": angler2_dead_penalty,
                        "dq": angler2_disqualified,
                        "buy": angler2_buy_in,
                    },
                )
            saved_count += 1

        # Save team result if both anglers exist
        if angler1_id and angler2_id:
            # Ensure consistent ordering (both are int at this point)
            if int(angler1_id) > int(angler2_id):
                angler1_id, angler2_id = angler2_id, angler1_id

            team_weight = (
                angler1_weight + angler2_weight - angler1_dead_penalty - angler2_dead_penalty
            )

            existing_team = qs.fetch_one(
                """SELECT id FROM team_results WHERE tournament_id = :tid
                   AND angler1_id = :a1 AND angler2_id = :a2""",
                {"tid": tournament_id, "a1": angler1_id, "a2": angler2_id},
            )

            if existing_team:
                qs.execute(
                    "UPDATE team_results SET total_weight = :weight WHERE id = :id",
                    {"weight": team_weight, "id": existing_team["id"]},
                )
            else:
                qs.execute(
                    """INSERT INTO team_results (tournament_id, angler1_id, angler2_id, total_weight)
                       VALUES (:tid, :a1, :a2, :weight)""",
                    {
                        "tid": tournament_id,
                        "a1": angler1_id,
                        "a2": angler2_id,
                        "weight": team_weight,
                    },
                )

        team_num += 1

    return RedirectResponse(f"/tournaments/{tournament_id}", status_code=303)


@router.delete("/admin/tournaments/{tournament_id}/results/{result_id}")
async def delete_result(
    tournament_id: int,
    result_id: int,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)
    qs.execute(
        "DELETE FROM results WHERE id = :id AND tournament_id = :tid",
        {"id": result_id, "tid": tournament_id},
    )
    return JSONResponse({"success": True})


@router.delete("/admin/tournaments/{tournament_id}/team-results/{team_result_id}")
async def delete_team_result(
    tournament_id: int,
    team_result_id: int,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)
    qs.execute(
        "DELETE FROM team_results WHERE id = :id AND tournament_id = :tid",
        {"id": team_result_id, "tid": tournament_id},
    )
    return JSONResponse({"success": True})


@router.post("/admin/tournaments/{tournament_id}/toggle-complete")
async def toggle_tournament_complete(
    tournament_id: int,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)
    # Get current completion status
    current = qs.fetch_one("SELECT complete FROM tournaments WHERE id = :id", {"id": tournament_id})

    if not current:
        return JSONResponse({"error": "Tournament not found"}, status_code=404)

    # Toggle the completion status
    new_status = not current["complete"]
    qs.execute(
        "UPDATE tournaments SET complete = :status WHERE id = :id",
        {"status": new_status, "id": tournament_id},
    )

    return JSONResponse(
        {
            "success": True,
            "new_status": new_status,
            "message": f"Tournament marked as {'complete' if new_status else 'upcoming'}",
        }
    )
