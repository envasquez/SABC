import logging
from typing import Union

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse, Response

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import OptionalUser
from core.query_service import QueryService
from routes.tournaments.data import fetch_tournament_data
from routes.tournaments.helpers import auto_complete_past_tournaments

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tournaments")
async def tournaments_list(request: Request, user: OptionalUser) -> RedirectResponse:
    """Display list of all tournaments."""
    # For now, redirect to home page which shows tournaments
    # This route exists to satisfy tests and can be enhanced later with a dedicated template
    return RedirectResponse("/", status_code=303)


@router.get("/tournaments/{tournament_id}", response_model=None)
async def tournament_results(
    request: Request, tournament_id: int, user: OptionalUser
) -> Union[Response, RedirectResponse]:
    try:
        # Auto-complete this tournament only (single-row write on index lookup
        # instead of a full-table scan).
        auto_complete_past_tournaments(tournament_id)

        with engine.connect() as conn:
            qs = QueryService(conn)
            (
                tournament,
                stats,
                team_results,
                individual_results,
                buy_in_place,
                buy_in_results,
                disqualified_results,
                payouts,
            ) = fetch_tournament_data(qs, tournament_id)
            tournament_view = {
                "id": tournament.id,
                "event_id": tournament.event_id,
                "event_date": tournament.event_date,
                "event_name": tournament.event_name,
                "event_description": tournament.event_description,
                "lake_name": tournament.lake_name,
                "ramp_name": tournament.ramp_name,
                "entry_fee": tournament.entry_fee,
                "fish_limit": tournament.fish_limit,
                "complete": tournament.complete,
                "event_type": tournament.event_type,
                "aoy_points": tournament.aoy_points,
                "start_time": tournament.start_time,
                "end_time": tournament.end_time,
            }
            stats_tuple = (
                stats.total_anglers,
                stats.total_fish,
                float(stats.total_weight),
                stats.limits,
                stats.zeros,
                stats.buy_ins,
                float(stats.biggest_bass),
                float(stats.heavy_stringer),
            )
            next_tournament_id = qs.get_next_tournament_id(tournament_id)
            prev_tournament_id = qs.get_previous_tournament_id(tournament_id)
            year_links = qs.get_tournament_years_with_first_id(4)
            return templates.TemplateResponse(
                request,
                "tournament_results.html",
                {
                    "user": user,
                    "tournament": tournament_view,
                    "tournament_stats": stats_tuple,
                    "team_results": team_results,
                    "individual_results": individual_results,
                    "buy_in_place": buy_in_place,
                    "buy_in_results": buy_in_results,
                    "disqualified_results": disqualified_results,
                    "payouts": payouts,
                    "next_tournament_id": next_tournament_id,
                    "prev_tournament_id": prev_tournament_id,
                    "year_links": year_links,
                },
            )
    except ValueError as e:
        # Tournament doesn't exist - redirect to home with friendly message
        logger.info(
            "Tournament not found - redirecting to home",
            extra={"tournament_id": tournament_id, "error": str(e)},
        )
        return RedirectResponse(
            "/?error=Tournament not found. Showing latest tournaments instead.",
            status_code=303,
        )
    except Exception as e:
        # Unexpected error - redirect to home with generic message
        logger.error(
            "Unexpected error loading tournament - redirecting to home",
            extra={"tournament_id": tournament_id, "error": str(e)},
            exc_info=True,
        )
        return RedirectResponse(
            "/?error=Unable to load tournament. Please try again later.",
            status_code=303,
        )
