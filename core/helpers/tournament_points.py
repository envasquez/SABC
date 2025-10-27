from typing import Any, Dict, List

import pandas as pd


def calculate_tournament_points(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Calculate tournament places and points with proper weight-based ranking.

    Ranking rules (for place_finish):
    1. Total weight (descending - heaviest first)
    2. Big bass weight (tiebreaker - bigger wins)
    3. Pandas stable sort (if still tied)

    Points rules:
    - Members with fish: Sequential points (100, 99, 98...) with gaps when guests appear
    - Guests: Always 0 points, but placed by weight
    - Member after guest: Gets previous_member_points - 1
    - Member zeros: Get previous_member_points - 2
    - Buy-ins: Separate, placed after all regular results
    """
    if not results:
        return []

    df = pd.DataFrame(results)
    df["total_weight"] = df["total_weight"].astype(float)
    df["big_bass_weight"] = df["big_bass_weight"].astype(float)

    # Calculate net weight (total_weight - dead_fish_penalty)
    # This ensures penalties are accounted for in ranking and points
    if "dead_fish_penalty" in df.columns:
        df["dead_fish_penalty"] = df["dead_fish_penalty"].fillna(0).astype(float)
        df["total_weight"] = df["total_weight"] - df["dead_fish_penalty"]

    # Separate buy-ins and disqualified from regular results
    regular_results = df[~df["buy_in"] & ~df["disqualified"]].copy()
    buy_ins = df[df["buy_in"] & ~df["disqualified"]].copy()

    # Sort regular results by weight (DESC) then big_bass (DESC)
    regular_results = regular_results.sort_values(
        ["total_weight", "big_bass_weight"], ascending=[False, False]
    ).reset_index(drop=True)

    # Assign places with ties
    current_place = 1
    for i in range(len(regular_results)):
        if i == 0:
            regular_results.loc[i, "calculated_place"] = current_place
        else:
            # Check if tied with previous (same weight and big bass)
            prev_weight = regular_results.loc[i - 1, "total_weight"]
            prev_bass = regular_results.loc[i - 1, "big_bass_weight"]
            curr_weight = regular_results.loc[i, "total_weight"]
            curr_bass = regular_results.loc[i, "big_bass_weight"]

            if prev_weight == curr_weight and prev_bass == curr_bass:
                # Tied - same place as previous
                regular_results.loc[i, "calculated_place"] = regular_results.loc[
                    i - 1, "calculated_place"
                ]
            else:
                # Not tied - next place (dense ranking)
                current_place = i + 1
                regular_results.loc[i, "calculated_place"] = current_place

    # Assign points - walk through and handle members vs guests
    current_member_points = 100
    last_member_with_fish_points = None

    for i in range(len(regular_results)):
        is_member = regular_results.loc[i, "was_member"]
        has_fish = regular_results.loc[i, "total_weight"] > 0

        if is_member:
            if has_fish:
                # Member with fish gets current points, decrement by 1
                regular_results.loc[i, "calculated_points"] = current_member_points
                last_member_with_fish_points = current_member_points
                current_member_points -= 1
            else:
                # Member zero: last_fish_points - 2 (per bylaws)
                if last_member_with_fish_points is not None:
                    regular_results.loc[i, "calculated_points"] = last_member_with_fish_points - 2
                else:
                    # No members with fish yet (edge case)
                    regular_results.loc[i, "calculated_points"] = 98
        else:
            # Guest gets 0 points, doesn't affect member points progression
            regular_results.loc[i, "calculated_points"] = 0

    # Handle buy-ins separately
    if len(buy_ins) > 0:
        # Buy-ins come after all regular results
        if len(regular_results) > 0:
            last_regular_place = regular_results["calculated_place"].max()
            buy_ins["calculated_place"] = last_regular_place + 1

            # Buy-in points: last_fish_points - 4 (per bylaws)
            if last_member_with_fish_points is not None:
                buy_ins["calculated_points"] = last_member_with_fish_points - 4
            else:
                # No members with fish (edge case)
                buy_ins["calculated_points"] = 96
        else:
            buy_ins["calculated_place"] = 1
            buy_ins["calculated_points"] = 96

    # Combine all results
    if len(buy_ins) > 0:
        result_df = pd.concat([regular_results, buy_ins], ignore_index=True)
    else:
        result_df = regular_results

    # Ensure place is int
    result_df["calculated_place"] = result_df["calculated_place"].astype(int)
    result_df["calculated_points"] = result_df["calculated_points"].astype(int)

    return result_df.to_dict("records")
