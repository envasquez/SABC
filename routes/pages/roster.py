from typing import Any, Dict, List

from fastapi import APIRouter, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.query_service import QueryService

router = APIRouter()


def get_member_monthly_weights(
    qs: QueryService, member_ids: List[int], current_year: int, dialect_name: str
) -> Dict[int, Dict[str, List[float]]]:
    """
    Fetch monthly weight data for all members in a single query.
    Returns a dict mapping member_id -> {year: [12 monthly weights]}
    """
    if not member_ids:
        return {}

    # Query to get all monthly weights for all members at once
    if dialect_name == "sqlite":
        monthly_query = """
            SELECT r.angler_id,
                   CAST(strftime('%Y', e.date) AS INTEGER) as year,
                   CAST(strftime('%m', e.date) AS INTEGER) as month,
                   SUM(r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE r.angler_id IN ({})
              AND r.disqualified = FALSE
              AND CAST(strftime('%Y', e.date) AS INTEGER) >= 2023
            GROUP BY r.angler_id, CAST(strftime('%Y', e.date) AS INTEGER),
                     CAST(strftime('%m', e.date) AS INTEGER)
            ORDER BY r.angler_id, year, month
        """.format(",".join(str(id) for id in member_ids))
        results = qs.fetch_all(monthly_query, {})
    else:
        # PostgreSQL version using ANY for array
        monthly_query = """
            SELECT r.angler_id,
                   EXTRACT(YEAR FROM e.date)::INTEGER as year,
                   EXTRACT(MONTH FROM e.date)::INTEGER as month,
                   SUM(r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE r.angler_id = ANY(:member_ids)
              AND r.disqualified = FALSE
              AND EXTRACT(YEAR FROM e.date) >= 2023
            GROUP BY r.angler_id, EXTRACT(YEAR FROM e.date), EXTRACT(MONTH FROM e.date)
            ORDER BY r.angler_id, year, month
        """
        results = qs.fetch_all(monthly_query, {"member_ids": member_ids})

    # Initialize empty data structure for all members
    member_weights: Dict[int, Dict[str, List[float]]] = {}
    for member_id in member_ids:
        member_weights[member_id] = {}
        for year in range(2023, current_year + 1):
            member_weights[member_id][str(year)] = [0.0] * 12

    # Fill in the actual weights
    for row in results:
        angler_id = row["angler_id"]
        year_str = str(row["year"])
        month_idx = int(row["month"]) - 1  # Convert to 0-indexed
        weight = float(row["total_weight"] or 0)

        if angler_id in member_weights and year_str in member_weights[angler_id]:
            if 0 <= month_idx < 12:
                member_weights[angler_id][year_str][month_idx] = weight

    return member_weights


@router.get("/roster")
async def roster(request: Request) -> Any:
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

        # Get member IDs for weight chart data (only for actual members, not guests)
        member_ids = [m["id"] for m in members if m["member"]]

        # Fetch monthly weight data for all members
        member_monthly_weights = get_member_monthly_weights(
            qs, member_ids, current_year, dialect_name
        )

    user = get_user_optional(request)
    return templates.TemplateResponse(
        "roster.html",
        {
            "request": request,
            "user": user,
            "members": members,
            "member_weights": member_monthly_weights,
        },
    )
