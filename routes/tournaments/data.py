from typing import Any, List, Tuple

from core.helpers.tournament_points import calculate_tournament_points
from core.models import TournamentStats, TournamentWithEvent
from core.query_service import QueryService
from routes.tournaments.formatters import (
    format_buy_in_results,
    format_disqualified_results,
    format_individual_results,
    format_team_results,
)


def fetch_tournament_data(
    qs: QueryService, tournament_id: int
) -> Tuple[
    TournamentWithEvent,
    TournamentStats,
    List[Tuple[Any, ...]],
    List[Tuple[Any, ...]],
    int,
    List[Tuple[Any, ...]],
    List[Tuple[Any, ...]],
]:
    """Fetch all tournament data including results and statistics."""
    # Get tournament basic info
    tournament_data = qs.fetch_one(
        """SELECT t.id, t.event_id, e.date as event_date, e.name as event_name,
           e.description as event_description, t.lake_name, t.ramp_name, t.entry_fee,
           t.fish_limit, t.complete, e.event_type
           FROM tournaments t
           JOIN events e ON t.event_id = e.id
           WHERE t.id = :tournament_id""",
        {"tournament_id": tournament_id},
    )

    if not tournament_data:
        raise ValueError("Tournament not found")

    tournament = TournamentWithEvent(**tournament_data)

    # Get tournament statistics
    stats_data = qs.fetch_one(
        """SELECT
           COUNT(DISTINCT CASE WHEN r.disqualified = FALSE THEN r.angler_id END) as total_anglers,
           COALESCE(SUM(CASE WHEN r.disqualified = FALSE THEN r.num_fish ELSE 0 END), 0) as total_fish,
           COALESCE(SUM(CASE WHEN r.disqualified = FALSE THEN r.total_weight ELSE 0 END), 0) as total_weight,
           COUNT(DISTINCT CASE WHEN r.disqualified = FALSE AND r.num_fish >= :fish_limit THEN r.id END) as limits,
           COUNT(DISTINCT CASE WHEN r.disqualified = FALSE AND r.num_fish = 0 AND r.buy_in = FALSE THEN r.id END) as zeros,
           COUNT(DISTINCT CASE WHEN r.buy_in = TRUE THEN r.id END) as buy_ins,
           COALESCE(MAX(CASE WHEN r.disqualified = FALSE THEN r.big_bass_weight ELSE 0 END), 0) as biggest_bass,
           COALESCE(MAX(CASE WHEN r.disqualified = FALSE THEN r.total_weight ELSE 0 END), 0) as heavy_stringer
           FROM results r
           WHERE r.tournament_id = :id""",
        {"id": tournament_id, "fish_limit": tournament.fish_limit or 5},
    )

    stats = TournamentStats(**stats_data) if stats_data else TournamentStats()

    # Get and format team results
    team_results_raw = qs.get_team_results(tournament_id)
    team_results = format_team_results(team_results_raw)

    # Get and format individual results
    individual_results_raw = qs.get_tournament_results(tournament_id)
    calculated_results = calculate_tournament_points(individual_results_raw)
    individual_results = format_individual_results(calculated_results)

    # Get and format buy-in results
    buy_in_place, buy_in_results = format_buy_in_results(calculated_results)

    # Get and format disqualified results
    disqualified_raw = qs.fetch_all(
        """SELECT a.name, a.member, r.was_member
           FROM results r
           JOIN anglers a ON r.angler_id = a.id
           WHERE r.tournament_id = :id AND r.disqualified = TRUE""",
        {"id": tournament_id},
    )
    disqualified_results = format_disqualified_results(disqualified_raw)

    return (
        tournament,
        stats,
        team_results,
        individual_results,
        buy_in_place,
        buy_in_results,
        disqualified_results,
    )
