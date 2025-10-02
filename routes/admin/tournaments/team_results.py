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
    if isinstance(user, RedirectResponse):
        return user

    form = await request.form()
    qs = QueryService(conn)

    try:
        angler1_id = int(form.get("angler1_id"))
        angler2_id = int(form.get("angler2_id")) if form.get("angler2_id") else None
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
        # Check if team_result_id was provided (edit mode)
        team_result_id = form.get("team_result_id")
        if team_result_id:
            existing = qs.fetch_one(
                "SELECT id FROM team_results WHERE id = :id",
                {"id": int(team_result_id)},
            )
        else:
            # Check for existing team by angler combination
            if angler2_id is None:
                # Solo angler - check for NULL angler2_id
                existing = qs.fetch_one(
                    """SELECT id FROM team_results
                       WHERE tournament_id = :tid
                       AND angler1_id = :a1 AND angler2_id IS NULL""",
                    {"tid": tournament_id, "a1": angler1_id},
                )
            else:
                # Team - check both angler combinations
                existing = qs.fetch_one(
                    """SELECT id FROM team_results
                       WHERE tournament_id = :tid
                       AND ((angler1_id = :a1 AND angler2_id = :a2)
                            OR (angler1_id = :a2 AND angler2_id = :a1))""",
                    {"tid": tournament_id, "a1": angler1_id, "a2": angler2_id},
                )
        if existing:
            qs.execute(
                """UPDATE team_results
                   SET total_weight = :total_weight
                   WHERE id = :id""",
                {"total_weight": total_weight, "id": existing["id"]},
            )
        else:
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
        # Recalculate place_finish using actual weights from results table
        qs.execute(
            """WITH calculated_weights AS (
                   SELECT tr.id,
                          COALESCE(r1.total_weight, 0) + COALESCE(r2.total_weight, 0) as weight
                   FROM team_results tr
                   LEFT JOIN results r1 ON tr.angler1_id = r1.angler_id
                       AND tr.tournament_id = r1.tournament_id
                   LEFT JOIN results r2 ON tr.angler2_id = r2.angler_id
                       AND tr.tournament_id = r2.tournament_id
                   WHERE tr.tournament_id = :tid
               ),
               ranked_teams AS (
                   SELECT id,
                          RANK() OVER (ORDER BY weight DESC) as place
                   FROM calculated_weights
               )
               UPDATE team_results tr
               SET place_finish = rt.place
               FROM ranked_teams rt
               WHERE tr.id = rt.id""",
            {"tid": tournament_id},
        )
        conn.commit()
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": True, "message": "Team result saved successfully"})
        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results", status_code=303
        )
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)
        raise
