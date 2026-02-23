from decimal import Decimal
from typing import Any, Dict, List, Tuple

from core.helpers.tournament_points import calculate_tournament_points
from core.models import TournamentStats, TournamentWithEvent
from core.query_service import QueryService
from routes.tournaments.formatters import (
    format_buy_in_results,
    format_disqualified_results,
    format_individual_results,
    format_team_results,
)

# Payout ratios per angler based on SABC bylaws (Article V)
# Entry fee: $50.00 per boat breakdown (100% payout per bylaws):
#   - First Place: $20.00
#   - Second Place: $14.00
#   - Third Place: $8.00
#   - Big Bass Pot: $8.00 (only if bass > 5 lbs, member only)
PAYOUT_FIRST_PLACE_PER_BOAT = Decimal("20.00")
PAYOUT_SECOND_PLACE_PER_BOAT = Decimal("14.00")
PAYOUT_THIRD_PLACE_PER_BOAT = Decimal("8.00")
PAYOUT_BIG_BASS_PER_BOAT = Decimal("8.00")
BIG_BASS_MINIMUM_WEIGHT = Decimal("5.0")  # Must be over 5 lbs to qualify

# Legacy rate for calculating carryover from old individual-format tournaments
# Old format was $25/angler with $4 to big bass pot
LEGACY_BIG_BASS_PER_ANGLER = Decimal("4.00")


def calculate_big_bass_carryover(qs: QueryService, tournament_id: int, event_date: str) -> Decimal:
    """Calculate the big bass carryover for a tournament by looking at previous tournaments.

    The big bass pot rolls over when no member catches a bass > 5 lbs.
    We scan backwards through tournaments until we find one where a member won,
    accumulating the pot from each tournament where it wasn't won.

    Handles both formats:
    - Individual format (old): Uses results table, $4/angler
    - Team format (new): Uses team_results table, $8/boat

    Args:
        qs: QueryService instance
        tournament_id: The tournament to calculate carryover for
        event_date: The date of the tournament

    Returns:
        The accumulated carryover amount from previous tournaments
    """
    # Get all previous tournaments that have been fished (have results or team_results)
    # Include both individual format (results) and team format (team_results)
    previous_tournaments = qs.fetch_all(
        """SELECT t.id, e.date, COALESCE(t.aoy_points, TRUE) as is_individual_format,
                  COUNT(DISTINCT r.angler_id) as angler_count,
                  COUNT(DISTINCT tr.id) as boat_count,
                  MAX(CASE WHEN r.was_member = TRUE AND r.big_bass_weight > :min_weight
                           AND r.disqualified = FALSE THEN 1 ELSE 0 END) as member_won_big_bass
           FROM tournaments t
           JOIN events e ON t.event_id = e.id
           LEFT JOIN results r ON r.tournament_id = t.id
           LEFT JOIN team_results tr ON tr.tournament_id = t.id
           WHERE e.date < :event_date
           GROUP BY t.id, e.date, t.aoy_points
           HAVING COUNT(r.id) > 0 OR COUNT(tr.id) > 0
           ORDER BY e.date DESC""",
        {"event_date": event_date, "min_weight": float(BIG_BASS_MINIMUM_WEIGHT)},
    )

    carryover = Decimal("0.00")

    for t in previous_tournaments:
        member_won = t["member_won_big_bass"] == 1

        if member_won:
            # A member won big bass at this tournament - pot was paid out
            # Stop accumulating, carryover resets after this tournament
            break

        # No member won big bass - add this tournament's contribution to carryover
        # Determine format by which table has data, not just aoy_points flag
        angler_count = t["angler_count"] or 0
        boat_count = t["boat_count"] or 0

        if angler_count > 0:
            # Has individual results - use $4/angler rate
            pot_contribution = LEGACY_BIG_BASS_PER_ANGLER * Decimal(angler_count)
        elif boat_count > 0:
            # Has team results only - use $8/boat rate
            pot_contribution = PAYOUT_BIG_BASS_PER_BOAT * Decimal(boat_count)
        else:
            # No results at all - skip
            pot_contribution = Decimal("0")

        carryover += pot_contribution

    return carryover


def calculate_tournament_payouts(
    total_boats: int,
    biggest_bass: Decimal,
    entry_fee: Decimal,
    big_bass_carryover: Decimal = Decimal("0.00"),
    member_caught_big_bass: bool = False,
) -> Dict[str, Any]:
    """Calculate tournament payouts based on SABC bylaws.

    Args:
        total_boats: Number of boats who paid entry fee ($50/boat)
        biggest_bass: Weight of the biggest bass caught (in lbs)
        entry_fee: Entry fee per boat (default $50.00)
        big_bass_carryover: Accumulated big bass pot from previous tournaments
        member_caught_big_bass: True if a member caught a bass > 5 lbs

    Returns:
        Dictionary with payout amounts for total_entry, first, second, third,
        big_bass_contribution, big_bass_carryover, big_bass_total, big_bass_won
    """
    boats = Decimal(total_boats)
    total_entry = entry_fee * boats

    first_place = PAYOUT_FIRST_PLACE_PER_BOAT * boats
    second_place = PAYOUT_SECOND_PLACE_PER_BOAT * boats
    third_place = PAYOUT_THIRD_PLACE_PER_BOAT * boats

    # This tournament's contribution to the big bass pot
    big_bass_contribution = PAYOUT_BIG_BASS_PER_BOAT * boats

    # Total pot available (this tournament + carryover from previous)
    big_bass_total = big_bass_contribution + big_bass_carryover

    # Big bass only pays out if a MEMBER catches a bass over 5 lbs
    # Guests cannot win the big bass pot (pot rolls over)
    big_bass_won = member_caught_big_bass

    return {
        "total_entry": total_entry,
        "first_place": first_place,
        "second_place": second_place,
        "third_place": third_place,
        "big_bass_contribution": big_bass_contribution,
        "big_bass_carryover": big_bass_carryover,
        "big_bass_total": big_bass_total,
        "big_bass_won": big_bass_won,
    }


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
    Dict[str, Decimal],
]:
    """Fetch all tournament data including results and statistics."""
    # Get tournament basic info
    tournament_data = qs.fetch_one(
        """SELECT t.id, t.event_id, e.date as event_date, e.name as event_name,
           e.description as event_description, t.lake_name, t.ramp_name, t.entry_fee,
           t.fish_limit, t.complete, e.event_type,
           COALESCE(t.big_bass_carryover, 0) as big_bass_carryover,
           COALESCE(t.aoy_points, TRUE) as aoy_points
           FROM tournaments t
           JOIN events e ON t.event_id = e.id
           WHERE t.id = :tournament_id""",
        {"tournament_id": tournament_id},
    )

    if not tournament_data:
        raise ValueError("Tournament not found")

    tournament = TournamentWithEvent(**tournament_data)

    # Get tournament statistics - use team_results for team format, results for standard
    if not tournament.aoy_points:
        # Team format: calculate stats from team_results
        stats_data = qs.fetch_one(
            """SELECT
               (SELECT COUNT(DISTINCT angler_id) FROM (
                   SELECT angler1_id as angler_id FROM team_results WHERE tournament_id = :id
                   UNION
                   SELECT angler2_id as angler_id FROM team_results WHERE tournament_id = :id AND angler2_id IS NOT NULL
               ) anglers) as total_anglers,
               COUNT(tr.id) as total_boats,
               COALESCE(SUM(tr.num_fish), 0) as total_fish,
               COALESCE(SUM(tr.total_weight), 0) as total_weight,
               0 as limits,
               COUNT(CASE WHEN tr.num_fish = 0 THEN 1 END) as zeros,
               0 as buy_ins,
               0 as biggest_bass,
               COALESCE(MAX(tr.total_weight), 0) as heavy_stringer
               FROM team_results tr
               WHERE tr.tournament_id = :id""",
            {"id": tournament_id},
        )
    else:
        # Standard format: calculate stats from individual results
        # total_boats = total_anglers for standard format (each angler pays entry)
        stats_data = qs.fetch_one(
            """SELECT
               COUNT(DISTINCT CASE WHEN r.disqualified = FALSE THEN r.angler_id END) as total_anglers,
               COUNT(DISTINCT CASE WHEN r.disqualified = FALSE THEN r.angler_id END) as total_boats,
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

    # Check if biggest bass was caught by a member (guests can't win big bass pot)
    # Only members at the time of the tournament (was_member) can win
    big_bass_winner = qs.fetch_one(
        """SELECT r.big_bass_weight, r.was_member, a.name
           FROM results r
           JOIN anglers a ON r.angler_id = a.id
           WHERE r.tournament_id = :id
           AND r.disqualified = FALSE
           AND r.big_bass_weight > :min_weight
           AND r.was_member = TRUE
           ORDER BY r.big_bass_weight DESC
           LIMIT 1""",
        {"id": tournament_id, "min_weight": float(BIG_BASS_MINIMUM_WEIGHT)},
    )
    member_has_qualifying_big_bass = big_bass_winner is not None

    # Check if the overall big bass was caught by a guest (for display purposes)
    overall_big_bass = qs.fetch_one(
        """SELECT r.big_bass_weight, r.was_member
           FROM results r
           WHERE r.tournament_id = :id
           AND r.disqualified = FALSE
           AND r.big_bass_weight > 0
           ORDER BY r.big_bass_weight DESC
           LIMIT 1""",
        {"id": tournament_id},
    )
    big_bass_caught_by_guest = (
        overall_big_bass is not None
        and overall_big_bass["big_bass_weight"] > 0
        and not overall_big_bass["was_member"]
    )

    # Calculate payouts based on bylaws
    entry_fee = Decimal(str(tournament.entry_fee)) if tournament.entry_fee else Decimal("25.00")
    # Dynamically calculate carryover from previous tournaments
    carryover = calculate_big_bass_carryover(qs, tournament_id, str(tournament.event_date))
    # Use total_boats for payout calculation (team format = boats, standard = anglers)
    payouts = calculate_tournament_payouts(
        total_boats=stats.total_boats,
        biggest_bass=stats.biggest_bass,
        entry_fee=entry_fee,
        big_bass_carryover=carryover,
        member_caught_big_bass=member_has_qualifying_big_bass,
    )
    # Add guest indicator for display
    payouts["big_bass_caught_by_guest"] = big_bass_caught_by_guest

    return (
        tournament,
        stats,
        team_results,
        individual_results,
        buy_in_place,
        buy_in_results,
        disqualified_results,
        payouts,
    )
