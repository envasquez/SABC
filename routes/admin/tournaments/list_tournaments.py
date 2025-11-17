from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import Connection

from core.deps import get_db, templates
from core.helpers.auth import require_admin
from core.query_service import QueryService

router = APIRouter()


@router.get("/admin/tournaments")
async def admin_tournaments_list(
    request: Request,
    user=Depends(require_admin),
    conn: Connection = Depends(get_db),
):
    if isinstance(user, RedirectResponse):
        return user

    qs = QueryService(conn)

    # Auto-complete past tournaments
    qs.auto_complete_past_tournaments()
    conn.commit()

    # Fetch all tournaments with event and lake information
    tournaments = qs.fetch_all(
        """
        SELECT
            t.id,
            t.complete,
            t.entry_fee,
            e.date,
            e.name,
            l.display_name as lake_name,
            (SELECT COUNT(*) FROM results WHERE tournament_id = t.id) as result_count,
            (SELECT COUNT(*) FROM team_results WHERE tournament_id = t.id) as team_result_count
        FROM tournaments t
        JOIN events e ON t.event_id = e.id
        LEFT JOIN lakes l ON t.lake_id = l.id
        ORDER BY e.date DESC
        """
    )

    for t in tournaments:
        t["total_participants"] = t["result_count"] + t["team_result_count"]

    return templates.TemplateResponse(
        "admin/tournaments.html", {"request": request, "user": user, "tournaments": tournaments}
    )
