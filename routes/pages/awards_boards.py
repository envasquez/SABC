"""Leaderboard assembly for the 2026+ team-format awards page.

The two season-stats queries each return one row per angler (or per boat
pairing) carrying *every* metric. This module turns one of those row sets
into the handful of ranked boards the template renders. Ranking ten rows
seven different ways in Python is cheaper than seven more ``GROUP BY``
round-trips, and it puts all the tiebreakers in one readable place.
"""

from decimal import Decimal
from typing import Any, Dict, List, Mapping, Sequence, Tuple

#: ``(board key, row key, tiebreaker row keys)`` for every ranked board.
#: Each board drops rows whose headline value is zero -- "Most Wins: 0" is
#: noise, not a standing.
BOARD_SPECS: Tuple[Tuple[str, str, Tuple[str, ...]], ...] = (
    ("wins", "firsts", ("top3", "money", "total_weight")),
    ("seconds", "seconds", ("firsts", "total_weight")),
    ("thirds", "thirds", ("firsts", "total_weight")),
    ("top3", "top3", ("firsts", "total_weight")),
    ("money", "money", ("firsts", "total_weight")),
    ("fish", "total_fish", ("total_weight",)),
    ("weight", "total_weight", ("total_fish",)),
)

#: Row key the full standings table is ordered by, most consistent first.
STANDINGS_SORT: Tuple[str, ...] = ("top3", "firsts", "total_weight", "total_fish")

#: Rows shown per category board. Ten is what the existing single-metric
#: award queries on this page already return.
BOARD_LIMIT = 10

#: Rows shown in the full standings table. The club fields a few dozen
#: members a season, so this shows everyone in practice; the cap only stops
#: a database holding years of guests from rendering a thousand-row wall.
STANDINGS_LIMIT = 50


def _rank(
    rows: Sequence[Dict[str, Any]], keys: Sequence[str], limit: int = 0
) -> List[Dict[str, Any]]:
    """Sort ``rows`` by ``keys`` descending, re-numbering ``rank`` in place.

    Rows tied on every key share a rank, so a template can render "T-2"
    rather than inventing an order the data does not support.
    """
    ordered = sorted(rows, key=lambda row: tuple(row[k] for k in keys), reverse=True)
    if limit:
        ordered = ordered[:limit]
    ranked: List[Dict[str, Any]] = []
    for position, row in enumerate(ordered, start=1):
        values = tuple(row[k] for k in keys)
        if ranked and values == ranked[-1]["_sort_values"]:
            rank, tied = ranked[-1]["rank"], True
            ranked[-1]["tied"] = True
        else:
            rank, tied = position, False
        ranked.append({**row, "rank": rank, "tied": tied, "_sort_values": values})
    for row in ranked:
        del row["_sort_values"]
    return ranked


def build_boards(
    stats_rows: Sequence[Mapping[str, Any]],
    earnings: Mapping[Any, Decimal],
    earnings_key: str,
) -> Dict[str, Any]:
    """Build every ranked board for one grain (anglers or boat pairings).

    Args:
        stats_rows: Rows from ``get_angler_season_stats_query`` or
            ``get_team_season_stats_query``.
        earnings: Season earnings from
            :func:`awards_money.calculate_season_earnings`, keyed to match
            ``earnings_key``.
        earnings_key: Row key to look ``earnings`` up by -- ``angler_id`` for
            the angler grain, ``team_key`` for the pairing grain.

    Returns:
        ``{"standings": [...], "standings_total": n, "boards": {...}}``.
        ``standings`` is capped at :data:`STANDINGS_LIMIT` while
        ``standings_total`` reports how many rows exist, so the template can
        say what it is leaving out. Numbers are coerced to ``int`` / ``float``
        so the template's ``%.2f`` formatting works regardless of whether the
        driver handed back ``Decimal`` (PostgreSQL) or ``float`` (SQLite
        under test).
    """
    rows: List[Dict[str, Any]] = []
    for source in stats_rows:
        row = dict(source)
        rows.append(
            {
                **row,
                "events": int(row["events"] or 0),
                "firsts": int(row["firsts"] or 0),
                "seconds": int(row["seconds"] or 0),
                "thirds": int(row["thirds"] or 0),
                "top3": int(row["top3"] or 0),
                "total_fish": int(row["total_fish"] or 0),
                "total_weight": float(row["total_weight"] or 0),
                "best_stringer": float(row["best_stringer"] or 0),
                "best_bass": float(row["best_bass"] or 0),
                "money": float(earnings.get(row[earnings_key], Decimal("0.00"))),
            }
        )

    boards = {
        key: _rank([r for r in rows if r[value_key]], (value_key, *ties), BOARD_LIMIT)
        for key, value_key, ties in BOARD_SPECS
    }
    return {
        "standings": _rank(rows, STANDINGS_SORT, STANDINGS_LIMIT),
        "standings_total": len(rows),
        "boards": boards,
    }
