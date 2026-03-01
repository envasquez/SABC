from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Connection

from core.deps import get_db
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_float, get_form_int
from core.query_service import QueryService

router = APIRouter()


@router.post("/admin/tournaments/{tournament_id}/team-results")
async def save_team_result(
    tournament_id: int,
    request: Request,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    form_data = await request.form()
    qs = QueryService(conn)

    try:
        angler1_id_val = get_form_int(form_data, "angler1_id")
        angler2_id = get_form_int(form_data, "angler2_id")

        if angler1_id_val is None:
            return JSONResponse({"error": "Angler 1 ID is required"}, status_code=400)

        angler1_id = angler1_id_val

        # Check if this is team format (direct weight entry)
        is_team_format = form_data.get("is_team_format") == "true"
        num_fish = 0

        if is_team_format:
            # Team format: use direct weight and fish count from form
            direct_weight = get_form_float(form_data, "total_weight", 0.0)
            total_weight = Decimal(str(direct_weight))
            num_fish = get_form_int(form_data, "num_fish") or 0
        else:
            # Standard format: calculate from individual results
            total_weight = Decimal("0")
            angler1_data = qs.fetch_one(
                "SELECT total_weight, num_fish FROM results WHERE tournament_id = :tid AND angler_id = :aid",
                {"tid": tournament_id, "aid": angler1_id},
            )
            if angler1_data:
                total_weight += Decimal(str(angler1_data["total_weight"] or 0))
                num_fish += angler1_data["num_fish"] or 0
            if angler2_id:
                angler2_data = qs.fetch_one(
                    "SELECT total_weight, num_fish FROM results WHERE tournament_id = :tid AND angler_id = :aid",
                    {"tid": tournament_id, "aid": angler2_id},
                )
                if angler2_data:
                    total_weight += Decimal(str(angler2_data["total_weight"] or 0))
                    num_fish += angler2_data["num_fish"] or 0
        # Check if team_result_id was provided (edit mode)
        team_result_id = get_form_int(form_data, "team_result_id")
        if team_result_id:
            existing = qs.fetch_one(
                "SELECT id FROM team_results WHERE id = :id",
                {"id": team_result_id},
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
                   SET total_weight = :total_weight, num_fish = :num_fish
                   WHERE id = :id""",
                {"total_weight": total_weight, "num_fish": num_fish, "id": existing["id"]},
            )
        else:
            qs.execute(
                """INSERT INTO team_results
                   (tournament_id, angler1_id, angler2_id, total_weight, num_fish)
                   VALUES (:tid, :a1, :a2, :total_weight, :num_fish)""",
                {
                    "tid": tournament_id,
                    "a1": angler1_id,
                    "a2": angler2_id,
                    "total_weight": total_weight,
                    "num_fish": num_fish,
                },
            )
        conn.commit()

        # Recalculate place_finish
        if is_team_format:
            # Team format: use stored total_weight directly
            qs.execute(
                """UPDATE team_results
                   SET place_finish = (
                       SELECT place FROM (
                           SELECT id,
                                  RANK() OVER (ORDER BY total_weight DESC) as place
                           FROM team_results
                           WHERE tournament_id = :tid
                       ) ranked_teams
                       WHERE ranked_teams.id = team_results.id
                   )
                   WHERE tournament_id = :tid""",
                {"tid": tournament_id},
            )
        else:
            # Standard format: calculate weights from individual results
            qs.execute(
                """UPDATE team_results
                   SET place_finish = (
                       SELECT place FROM (
                           WITH calculated_weights AS (
                               SELECT tr.id,
                                      COALESCE(r1.total_weight, 0) + COALESCE(r2.total_weight, 0) as weight
                               FROM team_results tr
                               LEFT JOIN results r1 ON tr.angler1_id = r1.angler_id
                                   AND tr.tournament_id = r1.tournament_id
                               LEFT JOIN results r2 ON tr.angler2_id = r2.angler_id
                                   AND tr.tournament_id = r2.tournament_id
                               WHERE tr.tournament_id = :tid
                           )
                           SELECT id,
                                  RANK() OVER (ORDER BY weight DESC) as place
                           FROM calculated_weights
                       ) ranked_teams
                       WHERE ranked_teams.id = team_results.id
                   )
                   WHERE tournament_id = :tid""",
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
