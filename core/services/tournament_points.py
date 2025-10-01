"""Tournament points calculation logic."""

from typing import Any, Dict, List

import pandas as pd


def calculate_tournament_points(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calculate tournament points for results using pandas."""
    if not results:
        return []

    df = pd.DataFrame(results)
    df["total_weight"] = df["total_weight"].astype(float)

    # Regular anglers (not buy-ins, not disqualified)
    regular = df[~df["buy_in"] & ~df["disqualified"]].copy()

    # Separate those with fish from those with zero weight
    fish = regular[regular["total_weight"] > 0].sort_values("total_weight", ascending=False).copy()
    zeros = regular[regular["total_weight"] == 0].copy()

    # Calculate points for anglers with fish
    if len(fish) > 0:
        fish["calculated_place"] = range(1, len(fish) + 1)
        fish["calculated_points"] = 101 - fish["calculated_place"]
        last_fish_points = fish["calculated_points"].min()
        # All zeros tied at next place after last fish
        zeros["calculated_place"] = len(fish) + 1
        zeros["calculated_points"] = last_fish_points - 2
    else:
        zeros["calculated_place"] = 1
        zeros["calculated_points"] = 98

    # Handle buy-ins
    buy_ins = df[df["buy_in"] & ~df["disqualified"]].copy()
    if len(buy_ins) > 0:
        if len(fish) > 0:
            # Buy-ins get 4 points less than the last person with fish
            buy_in_points = fish["calculated_points"].min() - 4
            if len(zeros) > 0:
                # Place after zeros
                buy_ins["calculated_place"] = zeros["calculated_place"].iloc[0] + 1
            else:
                # Place after fish
                buy_ins["calculated_place"] = len(fish) + 1
        else:
            # No fish at all - fallback
            buy_in_points = 95
            buy_ins["calculated_place"] = 1
        buy_ins["calculated_points"] = buy_in_points

    # Combine all results
    result_df = (
        pd.concat([fish, zeros, buy_ins], ignore_index=True)
        if len(buy_ins) > 0
        else pd.concat([fish, zeros], ignore_index=True)
    )

    return result_df.to_dict("records")
