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

    tournaments = qs.fetch_all()  # type: ignore[call-arg]

    for t in tournaments:
        t["total_participants"] = t["result_count"] + t["team_result_count"]

    return templates.TemplateResponse(
        "admin/tournaments.html", {"request": request, "user": user, "tournaments": tournaments}
    )
