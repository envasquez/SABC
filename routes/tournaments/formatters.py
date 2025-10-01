"""Result formatting helpers for tournament data."""

from typing import Any, List, Tuple


def format_team_results(team_results_raw: List[dict]) -> List[Tuple[Any, ...]]:
    """Format team results for template display."""
    formatted = []
    for r in team_results_raw:
        angler1_name = r.get("angler1_name", "")
        angler2_name = r.get("angler2_name", "")

        # Determine if solo or team
        is_solo = not angler2_name or r.get("angler2_id") is None
        team_size = 1 if is_solo else 2

        # Format team name
        if is_solo:
            team_name = angler1_name
        else:
            team_name = f"{angler1_name} / {angler2_name}"

        formatted.append(
            (
                r.get("place_finish", 0),
                team_name,
                r.get("total_fish", 0),
                float(r.get("total_weight", 0)),
                bool(r.get("angler1_was_member", True)),
                bool(r.get("angler2_was_member", True)),
                r.get("id", 0),
                team_size,
            )
        )

    return formatted


def format_individual_results(calculated_results: List[dict]) -> List[Tuple[Any, ...]]:
    """Format individual results (non-buy-in, non-disqualified)."""
    regular_results = [
        r for r in calculated_results if not r.get("buy_in") and not r.get("disqualified")
    ]

    return [
        (
            r["calculated_place"],
            r["angler_name"],
            r["num_fish"],
            float(r["total_weight"]),
            float(r.get("big_bass_weight", 0)),
            r["calculated_points"],
            bool(r.get("was_member", True)),
            r.get("id", 0),
        )
        for r in regular_results
    ]


def format_buy_in_results(calculated_results: List[dict]) -> Tuple[int, List[Tuple[Any, ...]]]:
    """Format buy-in results and return buy-in place."""
    buy_ins = [r for r in calculated_results if r.get("buy_in")]
    buy_in_place = buy_ins[0]["calculated_place"] if buy_ins else 0

    buy_in_results = [
        (
            r["angler_name"],
            buy_in_place,
            buy_ins[0]["calculated_points"] if buy_ins else 0,
            bool(r.get("was_member", True)),
        )
        for r in buy_ins
    ]

    return buy_in_place, buy_in_results


def format_disqualified_results(disqualified_raw: List[dict]) -> List[Tuple[str, bool]]:
    """Format disqualified results."""
    return [(r["name"], bool(r.get("was_member", True))) for r in disqualified_raw]
