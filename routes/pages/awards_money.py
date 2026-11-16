"""Season earnings for the 2026+ team-format awards page.

Money is not stored anywhere -- a tournament's payouts are derived from its
boat count, and the big bass pot rolls over between tournaments (and across
year boundaries) whenever nobody boats a qualifying 5 lb+ bass. The
tournament detail page already derives this per tournament via
``calculate_tournament_payouts``; this module walks a season's tournaments in
date order so the awards leaderboard adds up to exactly what those pages
show, rather than re-deriving the bylaws with a second set of constants.

Attribution:

* Place money is paid per boat ($20 / $14 / $8 per boat for 1st / 2nd / 3rd),
  and split evenly among the anglers in that boat.
* Ties in ``place_finish`` come from a ``RANK()`` window, so a two-way tie for
  1st yields places 1, 1, 3 and no 2nd. The payout slots the tied boats
  occupy are pooled and divided among them, which is the conventional
  tournament handling and keeps the season total equal to the sum of the
  per-tournament payouts.
* The big bass pot goes to the single highest qualifying bass boated by a
  boat with at least one member, matching the eligibility rule in
  ``routes/tournaments/data.py``.
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Dict, List, Tuple

from core.query_service import QueryService
from routes.pages.awards_helpers import TEAM_KEY_SQL, TEAM_NAME_SQL
from routes.tournaments.data import (
    BIG_BASS_MINIMUM_WEIGHT,
    PAYOUT_FIRST_PLACE_PER_BOAT,
    PAYOUT_SECOND_PLACE_PER_BOAT,
    PAYOUT_THIRD_PLACE_PER_BOAT,
    calculate_big_bass_carryover,
    calculate_tournament_payouts,
)

#: Per-boat payout for each paid place, in finishing order.
PLACE_PAYOUTS_PER_BOAT: Tuple[Decimal, ...] = (
    PAYOUT_FIRST_PLACE_PER_BOAT,
    PAYOUT_SECOND_PLACE_PER_BOAT,
    PAYOUT_THIRD_PLACE_PER_BOAT,
)

_CENTS = Decimal("0.01")


def _season_boats_query() -> str:
    """Every boat row for a year's team-format tournaments, in event order.

    ``boats`` (the payout multiplier) counts ALL rows of
    ``v_team_tournament_results`` for the tournament rather than only the
    ``source = 'team_results'`` ones, because that is what the tournament
    page's ``total_boats`` counts and the two numbers have to agree.
    """
    return f"""
        SELECT vttr.tournament_id,
               e.date AS event_date,
               {TEAM_KEY_SQL} AS team_key,
               {TEAM_NAME_SQL} AS team_name,
               vttr.angler1_id,
               vttr.angler2_id,
               vttr.total_weight,
               vttr.big_bass_weight,
               vttr.place_finish,
               (COALESCE(a1.member, FALSE) OR COALESCE(a2.member, FALSE)) AS has_member,
               (SELECT COUNT(*) FROM v_team_tournament_results b
                WHERE b.tournament_id = vttr.tournament_id) AS boats
        FROM v_team_tournament_results vttr
        JOIN tournaments t ON vttr.tournament_id = t.id
        JOIN events e ON t.event_id = e.id
        JOIN anglers a1 ON vttr.angler1_id = a1.id
        LEFT JOIN anglers a2 ON vttr.angler2_id = a2.id
        WHERE vttr.source = 'team_results' AND e.year = :year
        ORDER BY e.date, vttr.tournament_id
    """


def _group_by_tournament(rows: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """Split date-ordered boat rows into one list per tournament."""
    grouped: List[List[Dict[str, Any]]] = []
    current_id = None
    for row in rows:
        if row["tournament_id"] != current_id:
            current_id = row["tournament_id"]
            grouped.append([])
        grouped[-1].append(row)
    return grouped


def _award_place_money(boats: List[Dict[str, Any]], boat_count: int) -> Dict[int, Decimal]:
    """Place money for one tournament, keyed by row index into ``boats``.

    Boats that weighed nothing cannot take a paying place even if ``RANK()``
    seated them in one (which happens only when fewer than three boats
    weighed in at all).
    """
    payable = [
        (i, row)
        for i, row in enumerate(boats)
        if row["place_finish"] is not None and Decimal(str(row["total_weight"] or 0)) > 0
    ]
    payable.sort(key=lambda pair: pair[1]["place_finish"])

    awards: Dict[int, Decimal] = {}
    slot = 0
    index = 0
    while index < len(payable) and slot < len(PLACE_PAYOUTS_PER_BOAT):
        place = payable[index][1]["place_finish"]
        tied = [pair for pair in payable[index:] if pair[1]["place_finish"] == place]
        pool = sum(
            PLACE_PAYOUTS_PER_BOAT[s] * boat_count
            for s in range(slot, min(slot + len(tied), len(PLACE_PAYOUTS_PER_BOAT)))
        )
        if pool:
            share = (Decimal(pool) / Decimal(len(tied))).quantize(_CENTS, rounding=ROUND_HALF_UP)
            for row_index, _ in tied:
                awards[row_index] = share
        slot += len(tied)
        index += len(tied)
    return awards


def _big_bass_winner(boats: List[Dict[str, Any]]) -> int:
    """Row index of the boat that wins the big bass pot, or -1 if it rolls.

    Eligibility mirrors ``routes/tournaments/data.py``: strictly over the 5 lb
    minimum, and at least one angler in the boat is a member.
    """
    best_index = -1
    best_weight = BIG_BASS_MINIMUM_WEIGHT
    for i, row in enumerate(boats):
        if not row["has_member"]:
            continue
        weight = Decimal(str(row["big_bass_weight"] or 0))
        if weight > best_weight:
            best_index, best_weight = i, weight
    return best_index


def calculate_season_earnings(
    qs: QueryService, year: int
) -> Tuple[Dict[int, Decimal], Dict[str, Decimal], Decimal]:
    """Season earnings per angler and per boat pairing for ``year``.

    Args:
        qs: Query service bound to an open connection.
        year: Season to total up. Only team-format (2026+) seasons are
            meaningful here; the per-boat payout constants are the 2026
            bylaws.

    Returns:
        ``(per_angler, per_team, total_paid)`` where ``per_angler`` is keyed
        by angler id with each angler's share of their boats' winnings (a
        two-angler boat splits 50/50), ``per_team`` is keyed by the
        ``team_key`` of :data:`awards_helpers.TEAM_KEY_SQL` with the full
        boat amount, and ``total_paid`` is the season's payout to all boats.
    """
    rows = qs.fetch_all(_season_boats_query(), {"year": year})
    per_angler: Dict[int, Decimal] = {}
    per_team: Dict[str, Decimal] = {}
    total_paid = Decimal("0.00")
    if not rows:
        return per_angler, per_team, total_paid

    tournaments = _group_by_tournament(rows)

    # Seed the rolling pot from every tournament before this season's first
    # one -- an unwon pot carries across the New Year, so a season cannot be
    # totalled in isolation.
    carryover = calculate_big_bass_carryover(
        qs, tournaments[0][0]["tournament_id"], str(tournaments[0][0]["event_date"])
    )

    for boats in tournaments:
        boat_count = int(boats[0]["boats"] or 0)
        winner_index = _big_bass_winner(boats)
        payouts = calculate_tournament_payouts(
            total_boats=boat_count,
            biggest_bass=max(Decimal(str(b["big_bass_weight"] or 0)) for b in boats),
            entry_fee=Decimal("50.00"),
            big_bass_carryover=carryover,
            member_caught_big_bass=winner_index >= 0,
        )

        awards = _award_place_money(boats, boat_count)
        if winner_index >= 0:
            awards[winner_index] = awards.get(winner_index, Decimal("0.00")) + Decimal(
                payouts["big_bass_total"]
            )
            carryover = Decimal("0.00")
        else:
            carryover = Decimal(payouts["big_bass_total"])

        for row_index, amount in awards.items():
            row = boats[row_index]
            total_paid += amount
            per_team[row["team_key"]] = per_team.get(row["team_key"], Decimal("0.00")) + amount
            seats = [row["angler1_id"], row["angler2_id"]]
            seats = [aid for aid in seats if aid is not None]
            share = (amount / Decimal(len(seats))).quantize(_CENTS, rounding=ROUND_HALF_UP)
            for angler_id in seats:
                per_angler[angler_id] = per_angler.get(angler_id, Decimal("0.00")) + share

    return per_angler, per_team, total_paid
