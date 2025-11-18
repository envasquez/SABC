import json
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import Connection

from core.deps import get_db, templates
from core.helpers.auth import require_admin
from core.query_service import QueryService
from routes.tournaments.helpers import auto_complete_past_tournaments

router = APIRouter()


@router.get("/admin/tournaments/{tournament_id}/enter-results")
async def enter_results_page(
    tournament_id: int,
    request: Request,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    # Auto-complete past tournaments using ORM session
    auto_complete_past_tournaments()

    qs = QueryService(conn)

    tournament = qs.get_tournament_by_id(tournament_id)
    if not tournament:
        return RedirectResponse("/admin/tournaments", status_code=303)

    anglers = qs.get_all_anglers()
    results = qs.get_tournament_results(tournament_id)
    team_results = qs.get_team_results(tournament_id)

    results_by_angler = {r["angler_id"]: r for r in results}
    teams_set = {(tr["angler1_id"], tr["angler2_id"]) for tr in team_results}

    edit_team_result_id = request.query_params.get("edit_team_result")
    edit_team_result_data = None
    if edit_team_result_id:
        edit_team_result_data = qs.fetch_one(
            """SELECT tr.*, a1.name as angler1_name, a2.name as angler2_name,
               r1.num_fish as angler1_fish, r1.total_weight as angler1_weight,
               r1.big_bass_weight as angler1_big_bass, r1.dead_fish_penalty as angler1_dead_penalty,
               r1.disqualified as angler1_disqualified, r1.buy_in as angler1_buy_in, r1.was_member as angler1_was_member,
               r2.num_fish as angler2_fish, r2.total_weight as angler2_weight,
               r2.big_bass_weight as angler2_big_bass, r2.dead_fish_penalty as angler2_dead_penalty,
               r2.disqualified as angler2_disqualified, r2.buy_in as angler2_buy_in, r2.was_member as angler2_was_member
               FROM team_results tr
               JOIN anglers a1 ON tr.angler1_id = a1.id
               LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
               LEFT JOIN results r1 ON tr.angler1_id = r1.angler_id AND tr.tournament_id = r1.tournament_id
               LEFT JOIN results r2 ON tr.angler2_id = r2.angler_id AND tr.tournament_id = r2.tournament_id
               WHERE tr.id = :id""",
            {"id": int(edit_team_result_id)},
        )
        if edit_team_result_data:
            edit_team_result_data = dict(edit_team_result_data)
            for key, value in edit_team_result_data.items():
                if isinstance(value, Decimal):
                    edit_team_result_data[key] = float(value)

    anglers_json = json.dumps(
        [{"id": a["id"], "name": a["name"], "member": a["member"]} for a in anglers]
    )
    existing_angler_ids = list(results_by_angler.keys())
    existing_angler_ids_json = json.dumps(existing_angler_ids)

    response = templates.TemplateResponse(
        "admin/enter_results.html",
        {
            "request": request,
            "user": user,
            "tournament": tournament,
            "anglers": anglers,
            "anglers_json": anglers_json,
            "existing_angler_ids_json": existing_angler_ids_json,
            "results_by_angler": results_by_angler,
            "team_results": team_results,
            "teams_set": teams_set,
            "edit_result_id": request.query_params.get("edit_result_id"),
            "edit_team_result": edit_team_result_id,
            "edit_team_result_data": edit_team_result_data,
        },
    )
    # Prevent browser caching so edit parameters are always fresh
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@router.post("/admin/tournaments/{tournament_id}/enter-results")
async def enter_results_redirect(tournament_id: int):
    return RedirectResponse(f"/admin/tournaments/{tournament_id}/enter-results", status_code=303)
