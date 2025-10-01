import json
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import Connection

from core.deps import get_admin_or_redirect, get_db, render
from core.query_service import QueryService

router = APIRouter()


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

    # Auto-complete past tournaments
    qs.auto_complete_past_tournaments()
    conn.commit()

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
            """SELECT tr.*, a1.name as angler1_name, a2.name as angler2_name FROM team_results tr
               JOIN anglers a1 ON tr.angler1_id = a1.id JOIN anglers a2 ON tr.angler2_id = a2.id WHERE tr.id = :id""",
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


@router.post("/admin/tournaments/{tournament_id}/enter-results")
async def enter_results_redirect(tournament_id: int):
    return RedirectResponse(f"/admin/tournaments/{tournament_id}/enter-results", status_code=303)
