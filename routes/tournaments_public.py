from fastapi import APIRouter, Request

from core.helpers.auth import get_user_optional
from core.helpers.common_queries import get_individual_results, get_tournament_results
from core.helpers.queries import get_tournament_stats
from core.helpers.template_helpers import render
from routes.dependencies import db, templates

router = APIRouter()


@router.get("/tournaments/{tournament_id}")
async def tournament_results(request: Request, tournament_id: int):
    user = get_user_optional(request)

    tournament = db(
        "SELECT t.id, t.event_id, e.date, e.name, e.description, t.lake_name, t.ramp_name, t.entry_fee, t.fish_limit, t.complete, e.event_type FROM tournaments t JOIN events e ON t.event_id = e.id WHERE t.id = :tournament_id",
        {"tournament_id": tournament_id},
    )

    if not tournament:
        return templates.TemplateResponse("404.html", {"request": request}, status_code=404)

    tournament = tournament[0]
    tournament_stats = get_tournament_stats(tournament_id, tournament[8])
    team_results = get_tournament_results(tournament_id)
    individual_results = get_individual_results(tournament_id)

    buy_in_place = db(
        "SELECT COUNT(*) + 1 FROM results r JOIN anglers a ON r.angler_id = a.id WHERE r.tournament_id = :tournament_id AND NOT r.disqualified AND r.buy_in = 0",
        {"tournament_id": tournament_id},
    )[0][0]

    buy_in_results = db(
        "SELECT a.name, :buy_in_place as place_finish, r.points, a.member FROM results r JOIN anglers a ON r.angler_id = a.id WHERE r.tournament_id = :tournament_id AND r.buy_in = 1 AND NOT r.disqualified ORDER BY a.name",
        {"tournament_id": tournament_id, "buy_in_place": buy_in_place},
    )

    return render(
        "tournament_results.html",
        request,
        user=user,
        tournament=tournament,
        tournament_stats=tournament_stats,
        team_results=team_results,
        individual_results=individual_results,
        buy_in_results=buy_in_results,
    )
