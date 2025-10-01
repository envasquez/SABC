from datetime import datetime

from fastapi import APIRouter, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional
from core.helpers.tournament_points import calculate_tournament_points
from core.query_service import QueryService
from routes.pages.awards_helpers import (
    get_big_bass_query,
    get_heavy_stringer_query,
    get_stats_query,
    get_tournament_results_query,
    get_years_query,
)

router = APIRouter()


@router.get("/awards")
@router.get("/awards/{year}")
async def awards(request: Request, year: int = None):
    user = get_user_optional(request)
    if year is None:
        year = datetime.now().year
    with engine.connect() as conn:
        qs = QueryService(conn)
        current_year = datetime.now().year
        available_years = qs.fetch_all(get_years_query(), {"year": current_year})
        years = [row["year"] for row in available_years]
        if not years:
            years = [datetime.now().year]
        if year not in years:
            year = years[0]
        stats = qs.fetch_one(get_stats_query(), {"year": year}) or {
            "total_tournaments": 0,
            "unique_anglers": 0,
            "total_fish": 0,
            "total_weight": 0.0,
            "avg_weight": 0.0,
        }
        all_tournament_results = qs.fetch_all(get_tournament_results_query(), {"year": year})
        tournaments_points, angler_totals = {}, {}
        current_tournament_id, current_tournament_results = None, []
        for result in all_tournament_results:
            if current_tournament_id != result["tournament_id"]:
                if current_tournament_results:
                    tournaments_points[current_tournament_id] = calculate_tournament_points(
                        current_tournament_results
                    )
                current_tournament_id, current_tournament_results = result["tournament_id"], []
            current_tournament_results.append(dict(result))
        if current_tournament_results:
            tournaments_points[current_tournament_id] = calculate_tournament_points(
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
        aoy_standings = list(angler_totals.values())
        aoy_standings.sort(key=lambda x: x["total_points"], reverse=True)
        heavy_stringer = qs.fetch_all(get_heavy_stringer_query(), {"year": year})
        big_bass = qs.fetch_all(get_big_bass_query(), {"year": year})
        return templates.TemplateResponse(
            "awards.html",
            {
                "request": request,
                "user": user,
                "current_year": year,
                "available_years": years,
                "aoy_standings": aoy_standings,
                "heavy_stringer": heavy_stringer[0] if heavy_stringer else None,
                "big_bass": big_bass[0] if big_bass else None,
                "year_stats": stats,
            },
        )
