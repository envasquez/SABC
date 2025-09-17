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

    return render(
        "admin/enter_results.html",
        request,
        user=user,
        tournament=tournament,
        anglers=anglers,
        results_by_angler=results_by_angler,
        team_results=team_results,
        teams_set=teams_set,
        edit_result_id=request.query_params.get("edit_result_id"),
        edit_team_result=request.query_params.get("edit_team_result"),
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

    if angler1_id == angler2_id:
        return JSONResponse({"error": "Team members must be different"}, status_code=400)

    # Ensure consistent ordering
    if angler1_id > angler2_id:
        angler1_id, angler2_id = angler2_id, angler1_id

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


@router.post("/admin/tournaments/{tournament_id}/complete")
async def complete_tournament(
    tournament_id: int,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)
    qs.execute("UPDATE tournaments SET complete = 1 WHERE id = :id", {"id": tournament_id})
    return RedirectResponse("/admin/tournaments", status_code=303)
