import logging

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import OptionalUser
from core.query_service import QueryService
from routes.tournaments.data import fetch_tournament_data
from routes.tournaments.helpers import auto_complete_past_tournaments

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tournaments")
async def tournaments_list(request: Request, user: OptionalUser):
    """Display list of all tournaments."""
    # For now, redirect to home page which shows tournaments
    # This route exists to satisfy tests and can be enhanced later with a dedicated template
    return RedirectResponse("/", status_code=303)


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, tournament_id: int, user: OptionalUser):
    try:
        # Auto-complete past tournaments using ORM session
        auto_complete_past_tournaments()

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
            ) = fetch_tournament_data(qs, tournament_id)
            tournament_tuple = (
                tournament.id,
                tournament.event_id,
                tournament.event_date,
                tournament.event_name,
                tournament.event_description,
                tournament.lake_name,
                tournament.ramp_name,
                tournament.entry_fee,
                tournament.fish_limit,
                tournament.complete,
                tournament.event_type,
            )
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
            response = templates.TemplateResponse(
                "tournament_results.html",
                {
                    "request": request,
                    "user": user,
                    "tournament": tournament_tuple,
                    "tournament_stats": stats_tuple,
                    "team_results": team_results,
                    "individual_results": individual_results,
                    "buy_in_place": buy_in_place,
                    "buy_in_results": buy_in_results,
                    "disqualified_results": disqualified_results,
                    "next_tournament_id": next_tournament_id,
                    "prev_tournament_id": prev_tournament_id,
                    "year_links": year_links,
                },
            )
            # Prevent browser caching of tournament results to ensure fresh data
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
            return response
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
