"""Data dashboard page showing club statistics and analytics."""

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional

router = APIRouter()


@router.get("/data")
async def data_dashboard(request: Request):
    """Display the club data dashboard with statistics and charts."""
    from core.query_service import QueryService

    user = get_user_optional(request)

    # Members-only page
    if not user or not user.get("member"):
        return RedirectResponse("/login?next=/data", status_code=302)

    with engine.connect() as conn:
        qs = QueryService(conn)

        # Get all the data
        available_years = qs.get_available_years()
        overview_stats = qs.get_club_overview_stats()
        lake_statistics = qs.get_lake_statistics()
        limits_zeros_by_year = qs.get_limits_zeros_by_year()
        big_bass_records = qs.get_big_bass_records(limit=10)
        membership_by_year = qs.get_membership_by_year()
        weight_trends = qs.get_weight_trends_by_year()
        winning_weights_by_year = qs.get_winning_weights_by_year()
        winning_weights_by_lake = qs.get_winning_weights_by_lake()
        winning_weights_by_lake_year = qs.get_winning_weights_by_lake_year()
        tournament_participation = qs.get_tournament_participation()

        return templates.TemplateResponse(
            "data.html",
            {
                "request": request,
                "user": user,
                "available_years": available_years,
                "overview_stats": overview_stats,
                "lake_statistics": lake_statistics,
                "limits_zeros_by_year": limits_zeros_by_year,
                "big_bass_records": big_bass_records,
                "membership_by_year": membership_by_year,
                "weight_trends": weight_trends,
                "winning_weights_by_year": winning_weights_by_year,
                "winning_weights_by_lake": winning_weights_by_lake,
                "winning_weights_by_lake_year": winning_weights_by_lake_year,
                "tournament_participation": tournament_participation,
            },
        )
