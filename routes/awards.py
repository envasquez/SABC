from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Request

from core.helpers.auth import get_user_optional
from core.helpers.common_queries import get_aoy_standings, get_big_bass, get_heavy_stringer
from core.helpers.template_helpers import render
from routes.dependencies import db

router = APIRouter()


@router.get("/awards")
@router.get("/awards/{year}")
async def awards(request: Request, year: Optional[int] = None):
    user = get_user_optional(request)

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

    aoy_standings = get_aoy_standings(year)
    heavy_stringer = get_heavy_stringer(year)
    big_bass = get_big_bass(year)

    year_stats = db(
        "SELECT COUNT(DISTINCT t.id) as total_tournaments, COUNT(DISTINCT a.id) as unique_anglers, SUM(r.num_fish) as total_fish, SUM(r.total_weight) as total_weight, AVG(r.total_weight) as avg_weight FROM tournaments t JOIN events e ON t.event_id = e.id JOIN results r ON t.id = r.tournament_id JOIN anglers a ON r.angler_id = a.id WHERE e.year = :year",
        {"year": year},
    )
    stats = year_stats[0] if year_stats else (0, 0, 0, 0.0, 0.0)

    return render(
        "awards.html",
        request,
        user=user,
        current_year=year,
        available_years=years,
        aoy_standings=aoy_standings,
        heavy_stringer=heavy_stringer[0] if heavy_stringer else None,
        big_bass=big_bass[0] if big_bass else None,
        year_stats={
            "total_tournaments": stats[0],
            "unique_anglers": stats[1],
            "total_fish": stats[2],
            "total_weight": stats[3],
            "avg_weight": stats[4],
        },
    )
