# -*- coding: utf-8 -*-
"""
Test Plan for Results & TeamResults (according to club rules)
- Guests can never be awarded points
- Guests cannot win big bass (only members)
- A result is not re-calculated if manually edited and "locked"
- If a person is DQ'd and awarded points, they get 3 less points than the last weighed (non-zero) place
- A person DQ'd should have the highest (number) place_finish, or tie any other DQ's
- Penalty weight is only calculated on record insert (i.e. re-saving does not re-calculate)
- A TeamResult is the addition of one or more results to create a cumulative result (test the math)
- TeamResult team_name needs to be displayed correctly (even for teams with 1 angler)
- If an angler is DQ'd and is part of a team, then the entire TeamResult is DQ'd

---------------------------------
Place/Point Scenarios to test for
----------------------------------
- All anglers weigh-in results: i.e. no zeros, no buy-ins
- All anglers zero: there can be buy-ins and dq's
- All anglers fish: i.e. there are no buy-ins, there can be dqs
- An angler is DQ'd and receives no points
- A person fishing solo wins the TeamResult
- Points are accurate:
    100 -> N: for weighed results
       N - 2: for zeros (fished, but didn't catch/weigh-in)
       N - 3: for DQ but awarded points (if weighed fish)
       N - 4: Buy-ins
"""
from decimal import Decimal
from typing import Optional

import pytest

from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament, get_big_bass_winner, set_points
from . import create_angler, create_angler_and_result


@pytest.mark.django_db
def test_guest_no_points() -> None:
    """Ensure that guests do not receive points ... and member points adjust accordinly.

    Create results for a tournament. Odd places will be members, even places will be guests.
    Ensure that guest points are zero, and member points start at max and decrement by 1 for each member result
    """
    tmnt: Tournament = Tournament.objects.create()
    for num in range(1, 11):
        angler: dict = {
            "first_name": "Angler",
            "last_name": f"{num}",
            "is_member": num % 2 == 0,
        }
        result: dict = {
            "tournament": tmnt,
            "total_weight": Decimal("5") + num,
            "num_fish": 5,
        }
        create_angler_and_result(**{"angler": angler, "result": result})

    set_points(tid=tmnt.id)
    previous: Optional[Result] = None
    for res in Result.objects.filter(tournament=tmnt).order_by("place_finish"):
        if res.place_finish % 2 == 0:
            assert res.points == 0
            continue
        assert res.points == previous.points - 1 if previous else tmnt.rules.max_points
        previous = res


@pytest.mark.django_db
def test_guest_cant_win_bb() -> None:
    """Ensure that a guest cannot win the big bass prize

    Create a big bass result for a guest that is greater than a big bass result for a member.
    The member should win.
    Delete the member result, and call get_big_bass_winner(tid) and it should return None
    """
    tmnt: Tournament = Tournament.objects.create()
    for idx in [1, 2]:
        kwargs: dict = {
            "angler": {"is_member": idx == 1},
            "result": {
                "tournament": tmnt,
                "total_weight": Decimal("10") if idx == 1 else Decimal("11"),
                "num_fish": 1,
                "big_bass_weight": Decimal("10") if idx == 1 else Decimal("11"),
            },
        }
        create_angler_and_result(**kwargs)

    winner: Result | None = get_big_bass_winner(tid=tmnt.id)
    assert winner.angler.member is True if winner else False

    if winner:
        winner.delete()
    assert get_big_bass_winner(tid=tmnt.id) is None


@pytest.mark.django_db
def test_penalty_wt_calculation() -> None:
    """Create a result and make it have 2 dead fish.

    The total_weight should == total_weight - 2 * dead_fish_penalty
    """
    tmnt: Tournament = Tournament.objects.create()
    kwargs: dict = {
        "angler": create_angler(),
        "tournament": tmnt,
        "num_fish": 5,
        "num_fish_dead": 2,
        "total_weight": Decimal("5"),
    }
    result: Result = Result.objects.create(**kwargs)
    assert result.total_weight == Decimal("5") - (2 * tmnt.rules.dead_fish_penalty)


@pytest.mark.django_db
def test_dq_with_points() -> None:
    """Ensures that a dq with points gets 3 less points, than the last weighed in results points

    Create 5 results (all members): R1: Non-zero winner, R2: Non-zero, R3: Non-zero, R4: Zero, R5: Buy-in
    Disqualify the #2 result. Points should be:
    1: R1 = MAX_POINTS
    2: R3 = R1 - 1
    3: R4 = R3 - 2
    4: R5 = R3 - 4
    5: R2 = R3 - 3
    """
    tmnt: Tournament = Tournament.objects.create()
    result_1: Result = create_angler_and_result(
        **{"result": {"tournament": tmnt, "total_weight": Decimal("25"), "num_fish": 5}}
    )
    result_2: Result = create_angler_and_result(
        **{
            "result": {
                "tournament": tmnt,
                "total_weight": Decimal("24"),
                "num_fish": 5,
                "disqualified": True,
            }
        }
    )
    result_3: Result = create_angler_and_result(
        **{"result": {"tournament": tmnt, "total_weight": Decimal("23"), "num_fish": 5}}
    )
    result_4: Result = create_angler_and_result(
        **{"result": {"tournament": tmnt, "total_weight": Decimal("00"), "num_fish": 0}}
    )
    result_5: Result = create_angler_and_result(
        **{"result": {"tournament": tmnt, "buy_in": True}}
    )

    set_points(tid=tmnt.id)
    # Make sure they finish in the order we expect (R1, R3, R4, R5, R2(dq'd))
    for place, result in enumerate(
        [result_1, result_3, result_4, result_5, result_2], start=1
    ):
        assert (
            result.angler
            == Result.objects.get(tournament=tmnt, place_finish=place).angler
        )

    winner: Result = Result.objects.get(tournament=tmnt, place_finish=1)
    second: Result = Result.objects.get(tournament=tmnt, place_finish=2)
    third: Result = Result.objects.get(tournament=tmnt, place_finish=3)
    fourth: Result = Result.objects.get(tournament=tmnt, place_finish=4)
    fifth: Result = Result.objects.get(tournament=tmnt, place_finish=5)

    assert result_1.angler == winner.angler and winner.points == tmnt.rules.max_points
    assert result_3.angler == second.angler and second.points == winner.points - 1
    assert result_4.angler == third.angler and third.points == second.points - 2
    assert result_5.angler == fourth.angler and fourth.points == second.points - 4
    assert result_2.angler == fifth.angler and fifth.points == second.points - 3


@pytest.mark.django_db
def test_team_result_dq() -> None:
    """Ensures that a DQ'd result is not added to a team result

    R1 is a non-zero result
    R2 is a non-zero DQ result
    Create a Team that consists of R1 & R2
    Verify that all team result stats are the same as R1
    """
    tmnt: Tournament = Tournament.objects.create()
    results: list = []
    for idx in [1, 2]:
        kwargs: dict = {
            "result": {
                "tournament": tmnt,
                "total_weight": Decimal("10"),
                "num_fish": 5,
                "disqualified": idx == 1,
            }
        }
        results.append(create_angler_and_result(**kwargs))

    team_result: TeamResult = TeamResult.objects.create(
        tournament=tmnt, result_1=results[0], result_2=results[1]
    )
    assert team_result.total_weight == results[1].total_weight
