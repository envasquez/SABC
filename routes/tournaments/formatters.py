from typing import Any, List, Tuple


def format_team_results(team_results_raw: List[dict]) -> List[Tuple[Any, ...]]:
    formatted = []
    for r in team_results_raw:
        angler1_name = r.get("angler1_name", "")
        angler2_name = r.get("angler2_name", "")
        is_solo = not angler2_name or r.get("angler2_id") is None
        team_size = 1 if is_solo else 2
        if is_solo:
            team_name = angler1_name
        else:
            team_name = f"{angler1_name} / {angler2_name}"
        # `r.get(k, 0)` would still return None when the key is present
        # with a NULL DB value — team_results.num_fish, place_finish,
        # total_weight, and big_bass_weight are all nullable in the
        # schema, and prod hit `int(None)` on at least one tournament 136
        # team row. `or 0` collapses both missing-key and explicit-None
        # back to the zero default.
        formatted.append(
            (
                int(r.get("place_finish") or 0),
                team_name,
                int(r.get("total_fish") or 0),
                float(r.get("total_weight") or 0),
                bool(r.get("angler1_was_member", True)),
                bool(r.get("angler2_was_member", True)),
                int(r.get("id") or 0),
                team_size,
            )
        )
    return formatted


def format_individual_results(calculated_results: List[dict]) -> List[Tuple[Any, ...]]:
    # `id` is None for team-format tournament rows: get_tournament_results
    # LEFT JOINs `results` onto v_angler_tournament_results, and team-format
    # anglers only have a team_results row (no individual results row), so
    # `r.id` comes back NULL. Numeric DB fields (num_fish, total_weight,
    # big_bass_weight) are also nullable in the schema. `r.get(k) or 0`
    # collapses both missing-key and explicit-None to zero. calculated_*
    # come from pandas and are guaranteed int via astype.
    regular_results = [
        r for r in calculated_results if not r.get("buy_in") and not r.get("disqualified")
    ]
    return [
        (
            int(r["calculated_place"]),
            r["angler_name"],
            int(r.get("num_fish") or 0),
            float(r.get("total_weight") or 0),
            float(r.get("big_bass_weight") or 0),
            int(r["calculated_points"]),
            bool(r.get("was_member", True)),
            int(r.get("id") or 0),
        )
        for r in regular_results
    ]


def format_buy_in_results(calculated_results: List[dict]) -> Tuple[int, List[Tuple[Any, ...]]]:
    # Same None-vs-missing trap as format_individual_results: buy-in rows
    # may originate from team-format tournaments with no `results.id`.
    buy_ins = [r for r in calculated_results if r.get("buy_in")]
    buy_in_place = int(buy_ins[0]["calculated_place"]) if buy_ins else 0

    buy_in_results = [
        (
            r["angler_name"],
            buy_in_place,
            int(buy_ins[0]["calculated_points"]) if buy_ins else 0,
            bool(r.get("was_member", True)),
            int(r.get("id") or 0),
        )
        for r in buy_ins
    ]
    return buy_in_place, buy_in_results


def format_disqualified_results(disqualified_raw: List[dict]) -> List[Tuple[str, bool]]:
    return [(r.get("name", "Unknown"), bool(r.get("was_member", True))) for r in disqualified_raw]
