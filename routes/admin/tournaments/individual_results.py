from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy import Connection

from core.deps import get_db
from core.helpers.auth import require_admin
from core.helpers.forms import get_form_bool, get_form_float, get_form_int
from core.query_service import QueryService

router = APIRouter()


@router.post("/admin/tournaments/{tournament_id}/results")
async def save_result(
    tournament_id: int,
    request: Request,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    """Save or update individual tournament result."""
    if isinstance(user, RedirectResponse):
        return user

    form_data = await request.form()
    qs = QueryService(conn)

    try:
        # Extract form data
        angler_id_val = get_form_int(form_data, "angler_id")
        if angler_id_val is None:
            return JSONResponse({"error": "Angler ID is required"}, status_code=400)

        angler_id = angler_id_val
        num_fish = get_form_int(form_data, "num_fish", 0) or 0
        gross_weight = Decimal(str(get_form_float(form_data, "total_weight", 0.0) or 0.0))
        big_bass_weight = Decimal(str(get_form_float(form_data, "big_bass_weight", 0.0) or 0.0))
        # Accept both "dead_fish" and "dead_fish_penalty" field names
        dead_fish_penalty = Decimal(
            str(
                get_form_float(form_data, "dead_fish_penalty", 0.0)
                or get_form_float(form_data, "dead_fish", 0.0)
                or 0.0
            )
        )
        # Calculate net weight (gross weight - penalty)
        total_weight = gross_weight - dead_fish_penalty
        disqualified = get_form_bool(form_data, "disqualified")
        buy_in = get_form_bool(form_data, "buy_in")
        was_member = get_form_bool(form_data, "was_member")

        # Check if result already exists
        existing = qs.fetch_one(
            "SELECT id FROM results WHERE tournament_id = :tid AND angler_id = :aid",
            {"tid": tournament_id, "aid": angler_id},
        )

        if existing:
            # Update existing result
            qs.execute(
                """UPDATE results
                   SET num_fish = :num_fish,
                       total_weight = :total_weight,
                       big_bass_weight = :big_bass_weight,
                       dead_fish_penalty = :dead_fish_penalty,
                       disqualified = :disqualified,
                       buy_in = :buy_in,
                       was_member = :was_member
                   WHERE id = :id""",
                {
                    "num_fish": num_fish,
                    "total_weight": total_weight,
                    "big_bass_weight": big_bass_weight,
                    "dead_fish_penalty": dead_fish_penalty,
                    "disqualified": disqualified,
                    "buy_in": buy_in,
                    "was_member": was_member,
                    "id": existing["id"],
                },
            )
        else:
            # Insert new result
            qs.execute(
                """INSERT INTO results
                   (tournament_id, angler_id, num_fish, total_weight, big_bass_weight,
                    dead_fish_penalty, disqualified, buy_in, was_member)
                   VALUES (:tid, :aid, :num_fish, :total_weight, :big_bass_weight,
                           :dead_fish_penalty, :disqualified, :buy_in, :was_member)""",
                {
                    "tid": tournament_id,
                    "aid": angler_id,
                    "num_fish": num_fish,
                    "total_weight": total_weight,
                    "big_bass_weight": big_bass_weight,
                    "dead_fish_penalty": dead_fish_penalty,
                    "disqualified": disqualified,
                    "buy_in": buy_in,
                    "was_member": was_member,
                },
            )

        # Auto-create/update team result if this completes a team pairing
        # Check if this angler has a teammate in this tournament
        teammate_result = qs.fetch_one(
            """SELECT r.angler_id,
                      r.total_weight as net_weight,
                      tr.id as team_result_id
               FROM team_results tr
               LEFT JOIN results r ON (
                   (tr.angler1_id = r.angler_id OR tr.angler2_id = r.angler_id)
                   AND r.tournament_id = tr.tournament_id
               )
               WHERE tr.tournament_id = :tid
               AND (tr.angler1_id = :aid OR tr.angler2_id = :aid)
               AND r.angler_id != :aid""",
            {"tid": tournament_id, "aid": angler_id},
        )

        if teammate_result:
            # Calculate combined team weight (total_weight already has penalty subtracted)
            teammate_net_weight = teammate_result.get("net_weight", 0) or 0
            team_total_weight = total_weight + Decimal(str(teammate_net_weight))

            # Update existing team result
            qs.execute(
                """UPDATE team_results
                   SET total_weight = :weight
                   WHERE id = :team_id""",
                {"weight": team_total_weight, "team_id": teammate_result["team_result_id"]},
            )

        conn.commit()

        # Check if this is an AJAX request
        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JSONResponse({"success": True, "message": "Result saved successfully"})

        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results", status_code=303
        )
    except Exception as e:
        # Return JSON error for AJAX requests
        if request.headers.get(
            "X-Requested-With"
        ) == "XMLHttpRequest" or "application/json" in request.headers.get("Accept", ""):
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)
        raise


@router.post("/admin/tournaments/{tournament_id}/delete-result/{result_id}")
async def delete_result(
    tournament_id: int,
    result_id: int,
    request: Request,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    """Delete an individual tournament result."""
    if isinstance(user, RedirectResponse):
        return user

    qs = QueryService(conn)

    try:
        # Delete the result
        qs.execute(
            "DELETE FROM results WHERE id = :id AND tournament_id = :tid",
            {"id": result_id, "tid": tournament_id},
        )
        conn.commit()

        # Return success response
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": True, "message": "Result deleted successfully"})

        return RedirectResponse(
            f"/admin/tournaments/{tournament_id}/enter-results", status_code=303
        )
    except Exception as e:
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return JSONResponse({"success": False, "error": str(e)}, status_code=400)
        raise
