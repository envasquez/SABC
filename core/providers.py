from datetime import datetime

from fastapi import Depends

from core.helpers.auth import get_user_optional
from core.helpers.common_queries import (
    get_aoy_standings,
    get_big_bass,
    get_heavy_stringer,
    get_individual_results,
    get_tournament_results,
)
from core.helpers.queries import get_tournament_stats
from routes.dependencies import db


async def get_tournament_data(tournament_id: int, user=Depends(get_user_optional)):
    tournament = db(
        "SELECT t.id, t.event_id, e.date, e.name, e.description, t.lake_name, t.ramp_name, t.entry_fee, t.fish_limit, t.complete, e.event_type FROM tournaments t JOIN events e ON t.event_id = e.id WHERE t.id = :tournament_id",
        {"tournament_id": tournament_id},
    )

    if not tournament:
        return None

    tournament = tournament[0]
    return {
        "user": user,
        "tournament": tournament,
        "tournament_stats": get_tournament_stats(tournament_id, tournament[8]),
        "team_results": get_tournament_results(tournament_id),
        "individual_results": get_individual_results(tournament_id),
        "buy_in_place": db(
            "SELECT COUNT(*) + 1 FROM results r JOIN anglers a ON r.angler_id = a.id WHERE r.tournament_id = :tournament_id AND NOT r.disqualified AND r.buy_in = 0",
            {"tournament_id": tournament_id},
        )[0][0],
        "buy_in_results": db(
            "SELECT a.name, :buy_in_place as place_finish, r.points, a.member FROM results r JOIN anglers a ON r.angler_id = a.id WHERE r.tournament_id = :tournament_id AND r.buy_in = 1 AND NOT r.disqualified ORDER BY a.name",
            {
                "tournament_id": tournament_id,
                "buy_in_place": db(
                    "SELECT COUNT(*) + 1 FROM results r JOIN anglers a ON r.angler_id = a.id WHERE r.tournament_id = :tournament_id AND NOT r.disqualified AND r.buy_in = 0",
                    {"tournament_id": tournament_id},
                )[0][0],
            },
        ),
    }


async def get_awards_data(year: int = None, user=Depends(get_user_optional)):
    if year is None:
        year = datetime.now().year

    current_year = datetime.now().year
    available_years = db(
        "SELECT DISTINCT year FROM events WHERE year IS NOT NULL AND year <= :year ORDER BY year DESC",
        {"year": current_year},
    )
    years = [row[0] for row in available_years]

    if not years:
        years = [datetime.now().year]

    if year not in years:
        year = years[0]

    year_stats = db(
        "SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT a.id) as unique_anglers, SUM(r.num_fish) as total_fish, SUM(r.total_weight) as total_weight, AVG(r.total_weight) as avg_weight FROM tournaments t JOIN events e ON t.event_id = e.id JOIN results r ON t.id = r.tournament_id JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year",
        {"year": year},
    )
    stats = year_stats[0] if year_stats else (0, 0, 0, 0.0, 0.0)

    return {
        "user": user,
        "current_year": year,
        "available_years": years,
        "aoy_standings": get_aoy_standings(year),
        "heavy_stringer": get_heavy_stringer(year),
        "big_bass": get_big_bass(year),
        "year_stats": {
            "total_tournaments": stats[0],
            "unique_anglers": stats[1],
            "total_fish": stats[2],
            "total_weight": stats[3],
            "avg_weight": stats[4],
        },
    }
