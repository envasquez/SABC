from typing import Any, Dict, List

import pandas as pd


def calculate_tournament_points(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not results:
        return []

    df = pd.DataFrame(results)
    df["total_weight"] = df["total_weight"].astype(float)

    regular = df[~df["buy_in"] & ~df["disqualified"]].copy()

    fish = regular[regular["total_weight"] > 0].sort_values("total_weight", ascending=False).copy()
    zeros = regular[regular["total_weight"] == 0].copy()

    if len(fish) > 0:
        fish["calculated_place"] = range(1, len(fish) + 1)
        fish["calculated_points"] = 101 - fish["calculated_place"]
        last_fish_points = fish["calculated_points"].min()
        zeros["calculated_place"] = len(fish) + 1
        zeros["calculated_points"] = last_fish_points - 2
    else:
        zeros["calculated_place"] = 1
        zeros["calculated_points"] = 98

    buy_ins = df[df["buy_in"] & ~df["disqualified"]].copy()
    if len(buy_ins) > 0:
        if len(fish) > 0:
            buy_in_points = fish["calculated_points"].min() - 4
            if len(zeros) > 0:
                buy_ins["calculated_place"] = zeros["calculated_place"].iloc[0] + 1
            else:
                buy_ins["calculated_place"] = len(fish) + 1
        else:
            buy_in_points = 95
            buy_ins["calculated_place"] = 1
        buy_ins["calculated_points"] = buy_in_points

    result_df = (
        pd.concat([fish, zeros, buy_ins], ignore_index=True)
        if len(buy_ins) > 0
        else pd.concat([fish, zeros], ignore_index=True)
    )
    return result_df.to_dict("records")
