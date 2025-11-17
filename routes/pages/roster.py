from fastapi import APIRouter, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.query_service import QueryService

router = APIRouter()


@router.get("/roster")
async def roster(request: Request):
    from core.helpers.timezone import now_local

    current_year = now_local().year
    with engine.connect() as conn:
        qs = QueryService(conn)

        # Detect database dialect for compatibility
        dialect_name = conn.dialect.name

        if dialect_name == "sqlite":
            # SQLite-compatible version (GROUP_CONCAT with DISTINCT can't have delimiter)
            members = qs.fetch_all(
                """SELECT a.id, a.name, a.email,
                   COALESCE(
                       (SELECT MAX(r2.was_member)
                        FROM results r2
                        JOIN tournaments t2 ON r2.tournament_id = t2.id
                        JOIN events e2 ON t2.event_id = e2.id
                        WHERE r2.angler_id = a.id
                        AND CAST(strftime('%Y', e2.date) AS INTEGER) = :year),
                       a.member
                   ) as member,
                   a.is_admin, a.password_hash, a.year_joined, a.phone, a.created_at,
                   (SELECT GROUP_CONCAT(position)
                    FROM (SELECT DISTINCT position FROM officer_positions
                          WHERE angler_id = a.id AND year = :year
                          ORDER BY position)) as officer_positions,
                   (SELECT MAX(e.date)
                    FROM results r
                    JOIN tournaments t ON r.tournament_id = t.id
                    JOIN events e ON t.event_id = e.id
                    WHERE r.angler_id = a.id) as last_tournament_date
                   FROM anglers a
                   WHERE a.name != 'Admin User' AND a.email != 'admin@sabc.com'
                   ORDER BY member DESC,
                            CASE WHEN (SELECT GROUP_CONCAT(position)
                                       FROM (SELECT DISTINCT position FROM officer_positions
                                             WHERE angler_id = a.id AND year = :year)) IS NOT NULL THEN 0 ELSE 1 END,
                            a.name""",
                {"year": current_year},
            )
        else:
            # PostgreSQL version
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
                   (SELECT STRING_AGG(DISTINCT position, ', ' ORDER BY position)
                    FROM officer_positions
                    WHERE angler_id = a.id AND year = :year) as officer_positions,
                   (SELECT MAX(e.date)
                    FROM results r
                    JOIN tournaments t ON r.tournament_id = t.id
                    JOIN events e ON t.event_id = e.id
                    WHERE r.angler_id = a.id) as last_tournament_date
                   FROM anglers a
                   WHERE a.name != 'Admin User' AND a.email != 'admin@sabc.com'
                   ORDER BY member DESC,
                            CASE WHEN (SELECT STRING_AGG(DISTINCT position, ', ' ORDER BY position)
                                       FROM officer_positions
                                       WHERE angler_id = a.id AND year = :year) IS NOT NULL THEN 0 ELSE 1 END,
                            a.name""",
                {"year": current_year},
            )

    user = get_user_optional(request)
    return templates.TemplateResponse(
        "roster.html", {"request": request, "user": user, "members": members}
    )
