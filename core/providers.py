from datetime import datetime

from fastapi import Depends

from core.db_schema import engine
from core.helpers.auth import get_user_optional
from core.query_service import QueryService


async def get_tournament_data(tournament_id: int, user=Depends(get_user_optional)):
    try:
        with engine.connect() as conn:
            qs = QueryService(conn)

            tournament = qs.fetch_one(
                """SELECT t.id, t.event_id, e.date, e.name, e.description,
                   t.lake_name, t.ramp_name, t.entry_fee, t.fish_limit,
                   t.complete, e.event_type
                   FROM tournaments t JOIN events e ON t.event_id = e.id
                   WHERE t.id = :tournament_id""",
                {"tournament_id": tournament_id},
            )

            if not tournament:
                return None

            # Get tournament statistics
            stats = qs.fetch_one(
                """SELECT COUNT(DISTINCT r.angler_id) as total_anglers,
                   MAX(r.total_weight) as max_weight,
                   MIN(r.total_weight) as min_weight,
                   AVG(r.total_weight) as avg_weight
                   FROM results r WHERE r.tournament_id = :id""",
                {"id": tournament_id},
            )

            # Get team results
            team_results = qs.get_team_results(tournament_id)

            # Get individual results
            individual_results = qs.get_tournament_results(tournament_id)

            # Get buy-in place
            buy_in_place = (
                qs.fetch_value(
                    """SELECT COUNT(*) + 1 FROM results r
                   WHERE r.tournament_id = :id
                   AND NOT r.disqualified AND r.buy_in = FALSE""",
                    {"id": tournament_id},
                )
                or 1
            )

            # Get buy-in results
            buy_in_results = qs.fetch_all(
                """SELECT a.name, :place as place_finish, r.points, a.member
                   FROM results r JOIN anglers a ON r.angler_id = a.id
                   WHERE r.tournament_id = :id AND r.buy_in = TRUE
                   AND NOT r.disqualified ORDER BY a.name""",
                {"id": tournament_id, "place": buy_in_place},
            )

            return {
                "user": user,
                "tournament": tournament,
                "tournament_stats": stats,
                "team_results": team_results,
                "individual_results": individual_results,
                "buy_in_place": buy_in_place,
                "buy_in_results": buy_in_results,
            }
    except Exception:
        return None


async def get_awards_data(year: int = None, user=Depends(get_user_optional)):
    if year is None:
        year = datetime.now().year

    with engine.connect() as conn:
        qs = QueryService(conn)

        current_year = datetime.now().year
        available_years = qs.fetch_all(
            """SELECT DISTINCT year FROM events
               WHERE year IS NOT NULL AND year <= :year
               ORDER BY year DESC""",
            {"year": current_year},
        )
        years = [row["year"] for row in available_years]

        if not years:
            years = [datetime.now().year]

        if year not in years:
            year = years[0]

        # Get year statistics
        stats = qs.fetch_one(
            """SELECT COUNT(DISTINCT t.id) as total_tournaments,
               COUNT(DISTINCT a.id) as unique_anglers,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight) as total_weight,
               AVG(r.total_weight) as avg_weight
               FROM tournaments t
               JOIN events e ON t.event_id = e.id
               JOIN results r ON t.id = r.tournament_id
               JOIN anglers a ON r.angler_id = a.id
               WHERE e.year = :year AND a.name != 'Admin User'""",
            {"year": year},
        ) or {
            "total_tournaments": 0,
            "unique_anglers": 0,
            "total_fish": 0,
            "total_weight": 0.0,
            "avg_weight": 0.0,
        }

        # Get AoY standings
        aoy_standings = qs.fetch_all(
            """SELECT a.name,
               SUM(r.points) as total_points,
               SUM(r.num_fish) as total_fish,
               SUM(r.total_weight) as total_weight,
               COUNT(r.tournament_id) as tournaments_fished
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND a.member = TRUE AND a.name != 'Admin User'
               GROUP BY a.id, a.name
               ORDER BY total_points DESC""",
            {"year": year},
        )

        # Get heavy stringer
        heavy_stringer = qs.fetch_all(
            """SELECT a.name, r.total_weight, r.num_fish, e.name as tournament_name, e.date
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND r.total_weight > 0 AND a.name != 'Admin User'
               ORDER BY r.total_weight DESC
               LIMIT 10""",
            {"year": year},
        )

        # Get big bass
        big_bass = qs.fetch_all(
            """SELECT a.name, r.big_bass_weight, e.name as tournament_name, e.date
               FROM results r
               JOIN anglers a ON r.angler_id = a.id
               JOIN tournaments t ON r.tournament_id = t.id
               JOIN events e ON t.event_id = e.id
               WHERE e.year = :year AND r.big_bass_weight >= 5.0 AND a.name != 'Admin User'
               ORDER BY r.big_bass_weight DESC
               LIMIT 10""",
            {"year": year},
        )

        return {
            "user": user,
            "current_year": year,
            "available_years": years,
            "aoy_standings": aoy_standings,
            "heavy_stringer": heavy_stringer,
            "big_bass": big_bass,
            "year_stats": stats,
        }
