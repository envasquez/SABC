from datetime import datetime

from fastapi import APIRouter, Depends, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import require_auth
from core.query_service import QueryService

router = APIRouter()


@router.get("/roster")
async def roster(request: Request, user=Depends(require_auth)):
    current_year = datetime.now().year
    with engine.connect() as conn:
        qs = QueryService(conn)
        members = qs.fetch_all(
            """SELECT a.id, a.name, a.email,
               COALESCE(
                   (SELECT bool_or(r2.was_member)
                    FROM results r2
                    JOIN tournaments t2 ON r2.tournament_id = t2.id
                    JOIN events e2 ON t2.event_id = e2.id
                    WHERE r2.angler_id = a.id
                    AND EXTRACT(YEAR FROM e2.date) = :year),
                   a.member
               ) as member,
               a.is_admin, a.password_hash, a.year_joined, a.phone, a.created_at,
               STRING_AGG(op.position, ', ' ORDER BY op.position) as officer_positions,
               MAX(e.date) as last_tournament_date
               FROM anglers a
               LEFT JOIN officer_positions op ON a.id = op.angler_id AND op.year = :year
               LEFT JOIN results r ON a.id = r.angler_id
               LEFT JOIN tournaments t ON r.tournament_id = t.id
               LEFT JOIN events e ON t.event_id = e.id
               WHERE a.name != 'Admin User' AND a.email != 'admin@sabc.com'
               GROUP BY a.id, a.name, a.email, a.is_admin, a.password_hash, a.year_joined, a.phone, a.created_at
               ORDER BY member DESC, CASE WHEN STRING_AGG(op.position, ', ' ORDER BY op.position) IS NOT NULL THEN 0 ELSE 1 END, a.name""",
            {"year": current_year},
        )
    return templates.TemplateResponse(
        "roster.html", {"request": request, "user": user, "members": members}
    )
