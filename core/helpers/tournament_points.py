from typing import Any, Dict, List

import pandas as pd


def calculate_tournament_points(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not results:
        return []

    df = pd.DataFrame(results)
    df["total_weight"] = df["total_weight"].astype(float)

    # Only members get points - filter by was_member field
    members = df[df["was_member"]].copy()
    non_members = df[~df["was_member"]].copy()

    regular = members[~members["buy_in"] & ~members["disqualified"]].copy()

    fish = regular[regular["total_weight"] > 0].sort_values("total_weight", ascending=False).copy()
    zeros = regular[regular["total_weight"] == 0].copy()

    if len(fish) > 0:
        fish["calculated_place"] = range(1, len(fish) + 1)
        fish["calculated_points"] = 101 - fish["calculated_place"]
        last_fish_points = fish["calculated_points"].min()
        # All member zeros get the same place (tied)
        zeros["calculated_place"] = len(fish) + 1
        zeros["calculated_points"] = last_fish_points - 2
    else:
        # If no fish, all zeros tie for first place
        zeros["calculated_place"] = 1
        zeros["calculated_points"] = 98

    buy_ins = members[members["buy_in"] & ~members["disqualified"]].copy()
    if len(buy_ins) > 0:
        if len(fish) > 0:
            buy_in_points = fish["calculated_points"].min() - 4
            if len(zeros) > 0:
                # Buy-ins come after all zeros (not just first zero)
                buy_ins["calculated_place"] = len(fish) + len(zeros) + 1
            else:
                buy_ins["calculated_place"] = len(fish) + 1
        else:
            buy_in_points = 95
            # If no fish, buy-ins come after all zeros
            if len(zeros) > 0:
                buy_ins["calculated_place"] = len(zeros) + 1
            else:
                buy_ins["calculated_place"] = 1
        buy_ins["calculated_points"] = buy_in_points

    # Non-members get actual place based on weight but 0 points
    if len(non_members) > 0:
        non_members_regular = non_members[
            ~non_members["buy_in"] & ~non_members["disqualified"]
        ].copy()
        non_members_with_fish = non_members_regular[non_members_regular["total_weight"] > 0].copy()
        non_members_zeros = non_members_regular[non_members_regular["total_weight"] == 0].copy()

        # Calculate place for non-members based on where they fall in the overall standings
        # Non-members with fish get placed after last member with fish or after last member zero
        if len(non_members_with_fish) > 0:
            # Combine all results to determine proper placement
            all_with_fish = pd.concat([fish, non_members_with_fish], ignore_index=True).sort_values(
                "total_weight", ascending=False
            )
            all_with_fish["calculated_place"] = range(1, len(all_with_fish) + 1)
            # Map places back to non_members_with_fish using merge
            place_mapping = all_with_fish[["angler_id", "calculated_place"]].copy()
            non_members_with_fish = non_members_with_fish.merge(
                place_mapping, on="angler_id", how="left", suffixes=("_old", "")
            )
            # Remove old calculated_place column if it exists
            if "calculated_place_old" in non_members_with_fish.columns:
                non_members_with_fish = non_members_with_fish.drop(columns=["calculated_place_old"])
            # Ensure calculated_place is int
            non_members_with_fish["calculated_place"] = non_members_with_fish[
                "calculated_place"
            ].astype(int)
            non_members_with_fish["calculated_points"] = 0

        if len(non_members_zeros) > 0:
            # Non-member zeros come after all member placements (fish + zeros + buy_ins)
            # Calculate the highest place among members
            max_member_place = 0
            if len(fish) > 0:
                max_member_place = max(max_member_place, fish["calculated_place"].max())
            if len(zeros) > 0:
                max_member_place = max(max_member_place, zeros["calculated_place"].max())
            if len(buy_ins) > 0:
                max_member_place = max(max_member_place, buy_ins["calculated_place"].max())
            # Non-member zeros get sequential places after all members
            non_members_zeros["calculated_place"] = range(
                max_member_place + 1, max_member_place + len(non_members_zeros) + 1
            )
            non_members_zeros["calculated_points"] = 0

        non_members = (
            pd.concat([non_members_with_fish, non_members_zeros], ignore_index=True)
            if len(non_members_with_fish) > 0 and len(non_members_zeros) > 0
            else non_members_with_fish
            if len(non_members_with_fish) > 0
            else non_members_zeros
        )

    result_df = (
        pd.concat([fish, zeros, buy_ins, non_members], ignore_index=True)
        if len(buy_ins) > 0 or len(non_members) > 0
        else pd.concat([fish, zeros], ignore_index=True)
    )
    return result_df.to_dict("records")
