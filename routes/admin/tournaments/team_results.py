from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Connection

from core.deps import get_admin_or_redirect, get_db
from core.query_service import QueryService

router = APIRouter()


@router.post("/admin/tournaments/{tournament_id}/team-results")
async def save_team_result(
    tournament_id: int,
    request: Request,
    user=Depends(get_admin_or_redirect),
    conn: Connection = Depends(get_db),
):
    """Save or update team tournament result."""
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    qs = QueryService(conn)

    try:
        # Extract form data
        angler1_id = int(form.get("angler1_id"))
        angler2_id = int(form.get("angler2_id")) if form.get("angler2_id") else None

        # Calculate total weight from individual results
        total_weight = Decimal("0")

        angler1_weight = qs.fetch_value(
            "SELECT total_weight FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_id, "aid": angler1_id},
        )
        if angler1_weight:
            total_weight += Decimal(str(angler1_weight))

        if angler2_id:
            angler2_weight = qs.fetch_value(
                "SELECT total_weight FROM results WHERE tournament_id = :tid AND angler_id = :aid",
                {"tid": tournament_id, "aid": angler2_id},
            )
            if angler2_weight:
                total_weight += Decimal(str(angler2_weight))

        # Check if team result already exists for these anglers
        existing = qs.fetch_one(
            """SELECT id FROM team_results
               WHERE tournament_id = :tid
               AND ((angler1_id = :a1 AND angler2_id = :a2)
                    OR (angler1_id = :a2 AND angler2_id = :a1))""",
            {"tid": tournament_id, "a1": angler1_id, "a2": angler2_id},
        )

        if existing:
            # Update existing team result
            qs.execute(
                """UPDATE team_results
                   SET total_weight = :total_weight
                   WHERE id = :id""",
                {"total_weight": total_weight, "id": existing["id"]},
            )
        else:
            # Insert new team result
            qs.execute(
                """INSERT INTO team_results
                   (tournament_id, angler1_id, angler2_id, total_weight)
                   VALUES (:tid, :a1, :a2, :total_weight)""",
                {
                    "tid": tournament_id,
                    "a1": angler1_id,
                    "a2": angler2_id,
                    "total_weight": total_weight,
                },
            )

        conn.commit()

        # Recalculate place_finish for all teams in this tournament
        qs.execute(
            """WITH ranked_teams AS (
                   SELECT id,
                          ROW_NUMBER() OVER (ORDER BY total_weight DESC) as place
                   FROM team_results
                   WHERE tournament_id = :tid
               )
               UPDATE team_results tr
               SET place_finish = rt.place
               FROM ranked_teams rt
               WHERE tr.id = rt.id""",
            {"tid": tournament_id},
        )

        conn.commit()

        # Check if this is an AJAX request
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": True, "message": "Team result saved successfully"})

        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results", status_code=303
        )
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)
        raise
