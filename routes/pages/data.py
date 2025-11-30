"""Data dashboard page showing club statistics and analytics."""

from typing import Any, Dict, List, Set

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import get_user_optional

router = APIRouter()


def transform_lake_usage_for_chart(
    lake_usage: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Transform lake usage data into Chart.js format for stacked bar chart."""
    # Get unique years and lakes
    years: List[int] = sorted(set(row["year"] for row in lake_usage))
    lakes: Set[str] = set(row["lake_name"] for row in lake_usage)

    # Create a lookup for quick access
    usage_lookup: Dict[tuple[int, str], int] = {
        (row["year"], row["lake_name"]): row["tournament_count"] for row in lake_usage
    }

    # Build datasets for each lake
    datasets: List[Dict[str, Any]] = []
    colors = [
        "#0d6efd",  # blue
        "#198754",  # green
        "#ffc107",  # yellow
        "#dc3545",  # red
        "#6f42c1",  # purple
        "#20c997",  # teal
        "#fd7e14",  # orange
        "#6c757d",  # gray
        "#0dcaf0",  # cyan
        "#d63384",  # pink
    ]

    for i, lake in enumerate(sorted(lakes)):
        datasets.append(
            {
                "label": lake,
                "data": [usage_lookup.get((year, lake), 0) for year in years],
                "backgroundColor": colors[i % len(colors)],
            }
        )

    return {"labels": years, "datasets": datasets}


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
        tournaments_by_year = qs.get_tournaments_by_year()
        participation_trends = qs.get_participation_trends()
        lake_statistics = qs.get_lake_statistics()
        lake_usage_by_year = qs.get_lake_usage_by_year()
        catch_distribution = qs.get_catch_distribution()
        limits_zeros_by_year = qs.get_limits_zeros_by_year()
        big_bass_records = qs.get_big_bass_records(limit=10)
        membership_by_year = qs.get_membership_by_year()
        weight_trends = qs.get_weight_trends_by_year()

        # Transform lake usage data for chart
        lake_chart_data = transform_lake_usage_for_chart(lake_usage_by_year)

        return templates.TemplateResponse(
            "data.html",
            {
                "request": request,
                "user": user,
                "available_years": available_years,
                "overview_stats": overview_stats,
                "tournaments_by_year": tournaments_by_year,
                "participation_trends": participation_trends,
                "lake_statistics": lake_statistics,
                "lake_chart_data": lake_chart_data,
                "catch_distribution": catch_distribution,
                "limits_zeros_by_year": limits_zeros_by_year,
                "big_bass_records": big_bass_records,
                "membership_by_year": membership_by_year,
                "weight_trends": weight_trends,
            },
        )
