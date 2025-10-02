import logging

from fastapi import APIRouter, HTTPException, Request

from core.db_schema import engine
from core.deps import templates
from core.helpers.auth import OptionalUser
from core.query_service import QueryService
from routes.tournaments.data import fetch_tournament_data

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, tournament_id: int, user: OptionalUser):
    try:
        with engine.connect() as conn:
            qs = QueryService(conn)
            qs.auto_complete_past_tournaments()
            conn.commit()
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
            return templates.TemplateResponse(
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
                },
            )
    except ValueError as e:
        logger.error(f"ValueError for tournament {tournament_id}: {e}")
        raise HTTPException(status_code=404, detail="Tournament not found")
    except Exception as e:
        logger.error(f"Exception for tournament {tournament_id}: {e}", exc_info=True)
        raise HTTPException(status_code=404, detail="Tournament not found")
