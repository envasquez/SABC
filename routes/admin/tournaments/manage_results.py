import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Connection

from core.deps import get_db
from core.helpers.auth import require_admin
from core.query_service import QueryService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/admin/tournaments/{tournament_id}/manage-results")
async def manage_results_page(
    tournament_id: int,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    """Display tournament results management page."""
    from core.deps import templates

    if isinstance(user, RedirectResponse):
        return user

    # Get tournament and results data
    qs = QueryService(conn)
    try:
        from routes.tournaments.data import fetch_tournament_data

        (
            tournament,
            stats,
            team_results,
            individual_results,
            buy_in_place,
            buy_in_results,
            disqualified_results,
            _payouts,
        ) = fetch_tournament_data(qs, tournament_id)

        # Build fake request object for template
        from starlette.requests import Request as StarletteRequest

        scope = {
            "type": "http",
            "method": "GET",
            "path": f"/admin/tournaments/{tournament_id}/manage-results",
            "query_string": b"",
            "headers": [],
        }
        request = StarletteRequest(scope)

        return templates.TemplateResponse(
            "admin/tournaments/manage_results.html",
            {
                "request": request,
                "user": user,
                "tournament": tournament,
                "individual_results": individual_results,
                "team_results": team_results,
            },
        )
    except Exception as e:
        logger.error(f"Error loading manage results page: {e}")
        return RedirectResponse("/admin/events", status_code=303)


@router.delete("/admin/tournaments/{tournament_id}/results/{result_id}")
async def delete_result(
    tournament_id: int,
    result_id: int,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        logger.warning(f"Unauthorized delete attempt for result {result_id}")
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    logger.info(f"Deleting result {result_id} from tournament {tournament_id}")
    qs = QueryService(conn)

    # First get the angler_id from the result
    result = qs.fetch_one(
        "SELECT angler_id FROM results WHERE id = :id AND tournament_id = :tid",
        {"id": result_id, "tid": tournament_id},
    )

    if not result:
        logger.error(f"Result {result_id} not found in tournament {tournament_id}")
        return JSONResponse({"error": "Result not found"}, status_code=404)

    angler_id = result["angler_id"]
    logger.info(f"Found angler_id {angler_id} for result {result_id}")

    # Delete any team_results that include this angler
    logger.info(f"Deleting team_results for angler {angler_id} in tournament {tournament_id}")
    qs.execute(
        """DELETE FROM team_results
           WHERE tournament_id = :tid
           AND (angler1_id = :aid OR angler2_id = :aid)""",
        {"tid": tournament_id, "aid": angler_id},
    )

    # Now delete the individual result
    logger.info(f"Deleting individual result {result_id}")
    qs.execute(
        "DELETE FROM results WHERE id = :id AND tournament_id = :tid",
        {"id": result_id, "tid": tournament_id},
    )
    logger.info("Committing transaction")
    conn.commit()
    logger.info(f"Successfully deleted result {result_id}")
    return JSONResponse({"success": True})


@router.delete("/admin/tournaments/{tournament_id}/team-results/{team_result_id}")
async def delete_team_result(
    tournament_id: int,
    team_result_id: int,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)

    # First get the angler IDs from the team result
    team_result = qs.fetch_one(
        "SELECT angler1_id, angler2_id FROM team_results WHERE id = :id AND tournament_id = :tid",
        {"id": team_result_id, "tid": tournament_id},
    )

    if not team_result:
        return JSONResponse({"error": "Team result not found"}, status_code=404)

    # Delete individual results for both anglers (use separate DELETEs to avoid SQL injection)
    qs.execute(
        "DELETE FROM results WHERE tournament_id = :tid AND angler_id = :angler_id",
        {"tid": tournament_id, "angler_id": team_result["angler1_id"]},
    )
    if team_result["angler2_id"]:  # Handle solo team (angler2_id might be NULL)
        qs.execute(
            "DELETE FROM results WHERE tournament_id = :tid AND angler_id = :angler_id",
            {"tid": tournament_id, "angler_id": team_result["angler2_id"]},
        )

    # Delete the team result
    qs.execute(
        "DELETE FROM team_results WHERE id = :id AND tournament_id = :tid",
        {"id": team_result_id, "tid": tournament_id},
    )

    # Commit the transaction
    conn.commit()

    return JSONResponse({"success": True})


@router.post("/admin/tournaments/{tournament_id}/toggle-complete")
async def toggle_tournament_complete(
    tournament_id: int,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    """Toggle tournament complete status (legacy endpoint - complete status is mostly informational now)."""
    if isinstance(user, RedirectResponse):
        return JSONResponse({"error": "Unauthorized"}, status_code=403)

    qs = QueryService(conn)

    current = qs.fetch_one(
        "SELECT complete FROM tournaments WHERE id = :id",
        {"id": tournament_id},
    )

    if not current:
        return JSONResponse({"error": "Tournament not found"}, status_code=404)

    new_status = not current["complete"]
    qs.execute(
        "UPDATE tournaments SET complete = :status WHERE id = :id",
        {"status": new_status, "id": tournament_id},
    )
    conn.commit()

    return JSONResponse(
        {
            "success": True,
            "new_status": new_status,
            "message": f"Tournament marked as {'complete' if new_status else 'upcoming'}.",
        }
    )
