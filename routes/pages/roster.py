from typing import Any, Dict, List

from fastapi import APIRouter, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.query_service import QueryService

router = APIRouter()


def get_member_stats(
    qs: QueryService, member_ids: List[int], current_year: int, dialect_name: str
) -> Dict[int, Dict[str, Any]]:
    """
    Fetch tournament stats for all members in efficient batch queries.
    Returns a dict mapping member_id -> stats dict
    """
    if not member_ids:
        return {}

    # Initialize empty stats for all members
    member_stats: Dict[int, Dict[str, Any]] = {}
    for member_id in member_ids:
        member_stats[member_id] = {
            "team_tournaments": 0,
            "best_team_weight": 0.0,
            "big_bass": 0.0,
            "year_finishes": {},
            "all_time_first": 0,
            "all_time_second": 0,
            "all_time_third": 0,
        }
        # Initialize year finishes for each year
        for year in range(2023, current_year + 1):
            member_stats[member_id]["year_finishes"][year] = {
                "first": 0,
                "second": 0,
                "third": 0,
                "tournaments": 0,
            }

    id_list = ",".join(str(id) for id in member_ids)

    # Query 1: Team tournaments count and best team weight per member
    if dialect_name == "sqlite":
        team_stats_query = f"""
            SELECT tr.angler1_id as angler_id,
                   COUNT(DISTINCT tr.tournament_id) as team_tournaments,
                   MAX(tr.total_weight) as best_team_weight
            FROM team_results tr
            WHERE tr.angler1_id IN ({id_list})
            GROUP BY tr.angler1_id
            UNION ALL
            SELECT tr.angler2_id as angler_id,
                   COUNT(DISTINCT tr.tournament_id) as team_tournaments,
                   MAX(tr.total_weight) as best_team_weight
            FROM team_results tr
            WHERE tr.angler2_id IN ({id_list})
            GROUP BY tr.angler2_id
        """
    else:
        team_stats_query = f"""
            SELECT tr.angler1_id as angler_id,
                   COUNT(DISTINCT tr.tournament_id) as team_tournaments,
                   MAX(tr.total_weight) as best_team_weight
            FROM team_results tr
            WHERE tr.angler1_id IN ({id_list})
            GROUP BY tr.angler1_id
            UNION ALL
            SELECT tr.angler2_id as angler_id,
                   COUNT(DISTINCT tr.tournament_id) as team_tournaments,
                   MAX(tr.total_weight) as best_team_weight
            FROM team_results tr
            WHERE tr.angler2_id IN ({id_list})
            GROUP BY tr.angler2_id
        """

    team_results = qs.fetch_all(team_stats_query, {})
    # Aggregate results (member could appear in both angler1 and angler2)
    team_agg: Dict[int, Dict[str, float]] = {}
    for row in team_results:
        aid = row["angler_id"]
        if aid not in team_agg:
            team_agg[aid] = {"tournaments": 0, "best_weight": 0.0}
        team_agg[aid]["tournaments"] += row["team_tournaments"] or 0
        team_agg[aid]["best_weight"] = max(
            team_agg[aid]["best_weight"], float(row["best_team_weight"] or 0)
        )

    for aid, agg in team_agg.items():
        if aid in member_stats:
            member_stats[aid]["team_tournaments"] = agg["tournaments"]
            member_stats[aid]["best_team_weight"] = agg["best_weight"]

    # Query 2: Big bass per member
    big_bass_query = f"""
        SELECT r.angler_id,
               MAX(r.big_bass_weight) as big_bass
        FROM results r
        WHERE r.angler_id IN ({id_list})
          AND r.disqualified = FALSE
        GROUP BY r.angler_id
    """
    big_bass_results = qs.fetch_all(big_bass_query, {})
    for row in big_bass_results:
        aid = row["angler_id"]
        if aid in member_stats:
            member_stats[aid]["big_bass"] = float(row["big_bass"] or 0)

    # Query 3: Team finishes by year (1st, 2nd, 3rd place finishes)
    if dialect_name == "sqlite":
        finishes_query = f"""
            WITH ranked_results AS (
                SELECT tr.angler1_id, tr.angler2_id, tr.tournament_id, tr.total_weight,
                       CAST(strftime('%Y', e.date) AS INTEGER) as year,
                       ROW_NUMBER() OVER (
                           PARTITION BY tr.tournament_id
                           ORDER BY tr.total_weight DESC
                       ) as place
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE CAST(strftime('%Y', e.date) AS INTEGER) >= 2023
            )
            SELECT angler_id, year, place, COUNT(*) as cnt
            FROM (
                SELECT angler1_id as angler_id, year, place FROM ranked_results
                WHERE angler1_id IN ({id_list}) AND place <= 3
                UNION ALL
                SELECT angler2_id as angler_id, year, place FROM ranked_results
                WHERE angler2_id IN ({id_list}) AND place <= 3
            )
            GROUP BY angler_id, year, place
        """
    else:
        finishes_query = f"""
            WITH ranked_results AS (
                SELECT tr.angler1_id, tr.angler2_id, tr.tournament_id, tr.total_weight,
                       EXTRACT(YEAR FROM e.date)::INTEGER as year,
                       ROW_NUMBER() OVER (
                           PARTITION BY tr.tournament_id
                           ORDER BY tr.total_weight DESC
                       ) as place
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE EXTRACT(YEAR FROM e.date) >= 2023
            )
            SELECT angler_id, year, place, COUNT(*) as cnt
            FROM (
                SELECT angler1_id as angler_id, year, place FROM ranked_results
                WHERE angler1_id IN ({id_list}) AND place <= 3
                UNION ALL
                SELECT angler2_id as angler_id, year, place FROM ranked_results
                WHERE angler2_id IN ({id_list}) AND place <= 3
            ) sub
            GROUP BY angler_id, year, place
        """

    finishes_results = qs.fetch_all(finishes_query, {})
    for row in finishes_results:
        aid = row["angler_id"]
        year = int(row["year"])
        place = int(row["place"])
        cnt = int(row["cnt"] or 0)

        if aid in member_stats:
            # Update year finishes
            if year in member_stats[aid]["year_finishes"]:
                if place == 1:
                    member_stats[aid]["year_finishes"][year]["first"] += cnt
                elif place == 2:
                    member_stats[aid]["year_finishes"][year]["second"] += cnt
                elif place == 3:
                    member_stats[aid]["year_finishes"][year]["third"] += cnt

            # Update all-time totals
            if place == 1:
                member_stats[aid]["all_time_first"] += cnt
            elif place == 2:
                member_stats[aid]["all_time_second"] += cnt
            elif place == 3:
                member_stats[aid]["all_time_third"] += cnt

    # Query 4: Tournaments per year count
    if dialect_name == "sqlite":
        year_tournaments_query = f"""
            SELECT angler_id, year, COUNT(DISTINCT tournament_id) as tournaments
            FROM (
                SELECT tr.angler1_id as angler_id, tr.tournament_id,
                       CAST(strftime('%Y', e.date) AS INTEGER) as year
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler1_id IN ({id_list})
                  AND CAST(strftime('%Y', e.date) AS INTEGER) >= 2023
                UNION
                SELECT tr.angler2_id as angler_id, tr.tournament_id,
                       CAST(strftime('%Y', e.date) AS INTEGER) as year
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler2_id IN ({id_list})
                  AND CAST(strftime('%Y', e.date) AS INTEGER) >= 2023
            )
            GROUP BY angler_id, year
        """
    else:
        year_tournaments_query = f"""
            SELECT angler_id, year, COUNT(DISTINCT tournament_id) as tournaments
            FROM (
                SELECT tr.angler1_id as angler_id, tr.tournament_id,
                       EXTRACT(YEAR FROM e.date)::INTEGER as year
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler1_id IN ({id_list})
                  AND EXTRACT(YEAR FROM e.date) >= 2023
                UNION
                SELECT tr.angler2_id as angler_id, tr.tournament_id,
                       EXTRACT(YEAR FROM e.date)::INTEGER as year
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE tr.angler2_id IN ({id_list})
                  AND EXTRACT(YEAR FROM e.date) >= 2023
            ) sub
            GROUP BY angler_id, year
        """

    year_tournaments_results = qs.fetch_all(year_tournaments_query, {})
    for row in year_tournaments_results:
        aid = row["angler_id"]
        year = int(row["year"])
        tournaments = int(row["tournaments"] or 0)

        if aid in member_stats and year in member_stats[aid]["year_finishes"]:
            member_stats[aid]["year_finishes"][year]["tournaments"] = tournaments

    return member_stats


def get_member_monthly_weights(
    qs: QueryService, member_ids: List[int], current_year: int, dialect_name: str
) -> Dict[int, Dict[str, List[Dict[str, Any]]]]:
    """
    Fetch monthly weight data for all members in a single query.
    Returns a dict mapping member_id -> {year: [12 monthly data objects]}
    Each data object contains: {weight: float, buy_in: bool}
    """
    if not member_ids:
        return {}

    # Query to get all monthly weights for all members at once
    # Include buy_in flag for zero-weight detection
    if dialect_name == "sqlite":
        monthly_query = """
            SELECT r.angler_id,
                   CAST(strftime('%Y', e.date) AS INTEGER) as year,
                   CAST(strftime('%m', e.date) AS INTEGER) as month,
                   SUM(r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight,
                   MAX(CASE WHEN r.buy_in = 1 THEN 1 ELSE 0 END) as has_buy_in
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
                   SUM(r.total_weight - COALESCE(r.dead_fish_penalty, 0)) as total_weight,
                   BOOL_OR(r.buy_in) as has_buy_in
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
    # Each month is now an object with weight and buy_in flag
    member_weights: Dict[int, Dict[str, List[Dict[str, Any]]]] = {}
    for member_id in member_ids:
        member_weights[member_id] = {}
        for year in range(2023, current_year + 1):
            member_weights[member_id][str(year)] = [
                {"weight": 0.0, "buy_in": False} for _ in range(12)
            ]

    # Fill in the actual weights and buy_in flags
    for row in results:
        angler_id = row["angler_id"]
        year_str = str(row["year"])
        month_idx = int(row["month"]) - 1  # Convert to 0-indexed
        weight = float(row["total_weight"] or 0)
        has_buy_in = bool(row["has_buy_in"])

        if angler_id in member_weights and year_str in member_weights[angler_id]:
            if 0 <= month_idx < 12:
                member_weights[angler_id][year_str][month_idx] = {
                    "weight": weight,
                    "buy_in": has_buy_in,
                }

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
                    WHERE r.angler_id = a.id) as last_tournament_date,
                   (SELECT MIN(CASE position
                        WHEN 'President' THEN 1
                        WHEN 'Vice President' THEN 2
                        WHEN 'Secretary' THEN 3
                        WHEN 'Treasurer' THEN 4
                        WHEN 'Tournament Director' THEN 5
                        WHEN 'Assistant Tournament Director' THEN 6
                        WHEN 'Technology Director' THEN 7
                        ELSE 99 END)
                    FROM officer_positions
                    WHERE angler_id = a.id AND year = :year) as position_rank
                   FROM anglers a
                   WHERE a.name != 'Admin User' AND a.email != 'admin@sabc.com'
                   ORDER BY member DESC,
                            COALESCE((SELECT MIN(CASE position
                                WHEN 'President' THEN 1
                                WHEN 'Vice President' THEN 2
                                WHEN 'Secretary' THEN 3
                                WHEN 'Treasurer' THEN 4
                                WHEN 'Tournament Director' THEN 5
                                WHEN 'Assistant Tournament Director' THEN 6
                                WHEN 'Technology Director' THEN 7
                                ELSE 99 END)
                            FROM officer_positions
                            WHERE angler_id = a.id AND year = :year), 100),
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
                    WHERE r.angler_id = a.id) as last_tournament_date,
                   (SELECT MIN(CASE position
                        WHEN 'President' THEN 1
                        WHEN 'Vice President' THEN 2
                        WHEN 'Secretary' THEN 3
                        WHEN 'Treasurer' THEN 4
                        WHEN 'Tournament Director' THEN 5
                        WHEN 'Assistant Tournament Director' THEN 6
                        WHEN 'Technology Director' THEN 7
                        ELSE 99 END)
                    FROM officer_positions
                    WHERE angler_id = a.id AND year = :year) as position_rank
                   FROM anglers a
                   WHERE a.name != 'Admin User' AND a.email != 'admin@sabc.com'
                   ORDER BY member DESC,
                            COALESCE((SELECT MIN(CASE position
                                WHEN 'President' THEN 1
                                WHEN 'Vice President' THEN 2
                                WHEN 'Secretary' THEN 3
                                WHEN 'Treasurer' THEN 4
                                WHEN 'Tournament Director' THEN 5
                                WHEN 'Assistant Tournament Director' THEN 6
                                WHEN 'Technology Director' THEN 7
                                ELSE 99 END)
                            FROM officer_positions
                            WHERE angler_id = a.id AND year = :year), 100),
                            a.name""",
                {"year": current_year},
            )

        # Get member IDs for weight chart data (only for actual members, not guests)
        member_ids = [m["id"] for m in members if m["member"]]

        # Fetch monthly weight data for all members
        member_monthly_weights = get_member_monthly_weights(
            qs, member_ids, current_year, dialect_name
        )

        # Fetch stats for all members
        member_stats = get_member_stats(qs, member_ids, current_year, dialect_name)

    user = get_user_optional(request)
    return templates.TemplateResponse(
        "roster.html",
        {
            "request": request,
            "user": user,
            "members": members,
            "member_weights": member_monthly_weights,
            "member_stats": member_stats,
            "current_year": current_year,
        },
    )
