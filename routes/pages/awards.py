from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Request
from fastapi.responses import Response
from sqlalchemy.exc import SQLAlchemyError

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.helpers.logging import get_logger
from core.helpers.tournament_points import calculate_tournament_points
from core.query_service import QueryService
from routes.pages.awards_boards import build_boards
from routes.pages.awards_helpers import (
    get_angler_season_stats_query,
    get_big_bass_query,
    get_heavy_stringer_query,
    get_stats_query,
    get_team_big_bass_query,
    get_team_heavy_stringer_query,
    get_team_season_stats_query,
    get_tournament_results_query,
    get_years_query,
)
from routes.pages.awards_money import calculate_season_earnings

# Shared with the payout code, which keys the bylaws' per-boat rates off the
# same year. From this season on the page shows leaderboards built from boat
# finishes; earlier years keep the individual Angler-of-the-Year standings.
from routes.tournaments.data import TEAM_FORMAT_START_YEAR

logger = get_logger(__name__)

router = APIRouter()


def _calculate_aoy_standings(qs: QueryService, year: int) -> List[Dict[str, Any]]:
    """Angler-of-the-Year points standings for a pre-2026 season.

    Only called for individual-format years: the points model assigns 100 for
    1st, 99 for 2nd and so on from per-angler finishes, which team-format
    tournaments do not have. Running it against a team-format season does not
    merely return nothing useful -- it raises inside the points calculation,
    which used to surface as an ERROR log on every 2026 page view.
    """
    all_tournament_results = qs.fetch_all(get_tournament_results_query(), {"year": year})
    tournaments_points: Dict[int, List[Dict[str, Any]]] = {}
    angler_totals: Dict[int, Dict[str, Any]] = {}

    try:
        current_tournament_id: Optional[int] = None
        current_tournament_results: List[Dict[str, Any]] = []
        for result in all_tournament_results:
            if current_tournament_id != result["tournament_id"]:
                if current_tournament_results:
                    tournaments_points[current_tournament_id] = calculate_tournament_points(  # type: ignore[index]
                        current_tournament_results
                    )
                current_tournament_id, current_tournament_results = result["tournament_id"], []
            current_tournament_results.append(dict(result))
        if current_tournament_results:
            tournaments_points[current_tournament_id] = calculate_tournament_points(  # type: ignore[index]
                current_tournament_results
            )
        for tournament_results in tournaments_points.values():
            for result in tournament_results:
                angler_id = result["angler_id"]
                if angler_id not in angler_totals:
                    angler_totals[angler_id] = {
                        "name": result["angler_name"],
                        "total_points": 0,
                        "total_fish": 0,
                        "total_weight": 0.0,
                        "tournaments_fished": 0,
                    }
                angler_totals[angler_id]["total_points"] += result.get("calculated_points", 0)
                angler_totals[angler_id]["total_fish"] += result.get("num_fish", 0)
                angler_totals[angler_id]["total_weight"] += float(result.get("total_weight", 0))
                angler_totals[angler_id]["tournaments_fished"] += 1
    except (SQLAlchemyError, ValueError, KeyError) as e:
        # Log error but continue - show empty standings
        logger.error(f"Error calculating tournament points: {e}")

    # Filter to only include current members (matching profile page logic)
    current_members_query = "SELECT id FROM anglers WHERE member = true"
    current_member_ids = {row["id"] for row in qs.fetch_all(current_members_query, {})}
    standings = [data for aid, data in angler_totals.items() if aid in current_member_ids]
    standings.sort(key=lambda x: (x["total_points"], x["total_weight"]), reverse=True)
    return standings


@router.get("/awards")
@router.get("/awards/{year}")
def awards(request: Request, year: Optional[int] = None) -> Response:
    from core.helpers.timezone import now_local

    user = get_user_optional(request)
    if year is None:
        year = now_local().year
    with engine.connect() as conn:
        qs = QueryService(conn)
        current_year = now_local().year
        available_years = qs.fetch_all(get_years_query(), {"year": current_year})
        years = [row["year"] for row in available_years]
        if not years:
            years = [now_local().year]
        if year not in years:
            year = years[0]
        stats = qs.fetch_one(get_stats_query(), {"year": year}) or {
            "total_tournaments": 0,
            "unique_anglers": 0,
            "total_fish": 0,
            "total_weight": 0.0,
            "avg_weight": 0.0,
        }
        is_team_format = year >= TEAM_FORMAT_START_YEAR

        aoy_standings: List[Dict[str, Any]] = []
        angler_season: Dict[str, Any] = {}
        team_season: Dict[str, Any] = {}
        total_paid = 0.0
        if is_team_format:
            # 2026+ team format: single-event records come from the boat rows,
            # and the season boards are built at both grains.
            heavy_stringer = qs.fetch_all(get_team_heavy_stringer_query(), {"year": year})
            big_bass = qs.fetch_all(get_team_big_bass_query(), {"year": year})
            # Earnings are derived once and joined onto each grain by its own
            # key, because money is the one metric a GROUP BY cannot
            # aggregate -- the big bass pot rolls between tournaments.
            angler_earnings, team_earnings, season_paid = calculate_season_earnings(qs, year)
            total_paid = float(season_paid)
            angler_season = build_boards(
                qs.fetch_all(get_angler_season_stats_query(), {"year": year}),
                angler_earnings,
                "angler_id",
            )
            team_season = build_boards(
                qs.fetch_all(get_team_season_stats_query(), {"year": year}),
                team_earnings,
                "team_key",
            )
        else:
            # Pre-2026 individual format
            heavy_stringer = qs.fetch_all(get_heavy_stringer_query(), {"year": year})
            big_bass = qs.fetch_all(get_big_bass_query(), {"year": year})
            aoy_standings = _calculate_aoy_standings(qs, year)

        return templates.TemplateResponse(
            request,
            "awards.html",
            {
                "user": user,
                "current_year": year,
                "available_years": years,
                "aoy_standings": aoy_standings,
                "heavy_stringer": heavy_stringer[0] if heavy_stringer else None,
                "big_bass": big_bass[0] if big_bass else None,
                "year_stats": stats,
                "is_team_format": is_team_format,
                "angler_season": angler_season,
                "team_season": team_season,
                "total_paid": total_paid,
            },
        )
