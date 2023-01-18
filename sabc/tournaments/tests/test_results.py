# # -*- coding: utf-8 -*-
# """
# -------------------------------------------------------------
# Test Plan for Results & TeamResults (according to club rules)
# -------------------------------------------------------------
# - Guests can never be awarded points
# - Guests cannot win big bass (only members)
# - A result is not re-calculated if manually edited
# - If a person is DQ'd and awarded points, they get 3 less points than the last weighed (non-zero) place
# - A person DQ'd should have the highest (number) place_finish, or tie any other DQ's
# - Penalty weight is only calculated on record insert (i.e. re-saving does not re-calculate)
# - A TeamResult is the addition of one or more results to create a cumulative result (test the math)
# - TeamResult team_name needs to be displayed correctly (even for teams with 1 angler)
# - If an angler is DQ'd and is part of a team, then the entire TeamResult is DQ'd

# ---------------------------------
# Place/Point Scenarios to test for
# ----------------------------------
# - All anglers weigh-in results: i.e. no zeros, no buy-ins
# - All anglers zero: there can be buy-ins and dq's
# - All anglers fish: i.e. there are no buy-ins, there can be dqs
# - An angler is DQ'd and receives no points
# - A person fishing solo wins the TeamResult
# - Points are accurate:
#     100 -> N: for weighed results
#        N - 2: for zeros (fished, but didn't catch/weigh-in)
#        N - 3: for DQ but awarded points (if weighed fish)
#        N - 4: Buy-ins
# """
# from decimal import Decimal
# from typing import Any, Type

# from pytest import fixture
# from users.models import Angler

# from ..models.lakes import Lake, Ramp
# from ..models.payouts import PayOutMultipliers
# from ..models.results import Result, TeamResult
# from ..models.tournament import Tournament
# from . import create_angler


# @fixture
# def setUp() -> None:
#     pom: PayOutMultipliers = PayOutMultipliers.objects.create()
#     lake: Lake = Lake.objects.create(name="Test Lake")
#     ramp: Ramp = Ramp.objects.create(lake=lake, name="Test Ramp")
#     tmnt: dict[str, Any] = {"lake": lake, "ramp": ramp, "payout_multiplier": pom}
#     tmnt: Tournament = Tournament.objects.create(**tmnt)

# def test_guest_no_points() -> None:
#     # Create 3 records
#     # A1, A2, A3 = (member, guest, member)
#     #                 1st    2nd    3rd
#     #               MAX_PTS   0   MAX_PTS - 1
#     ...

# def test_guest_cant_win_bb() -> None:
#     # Create two results for a tournament 1: Member and 1: Guest
#     # Make the Guest have a larger fish over 5lbs than the Member
#     # get_big_bass_winner() should return the Member Result
#     member: Angler = create_angler(first_name="Angler1", last_name="Member", is_member=True)
#     guest: Angler = create_angler(first_name="Angler1", last_name="Guest", is_member=False)
#     Result.objects.create(
#         angler=member,
#         tournament=tmnt,
#         total_weight=Decimal("5"),
#         num_fish=1,
#         big_bass_weight=Decimal("5"),
#     )
#     Result.objects.create(
#         angler=guest,
#         tournament=tmnt,
#         total_weight=Decimal("6"),
#         num_fish=1,
#         big_bass_weight=Decimal("6"),
#     )
#     bb_winner: Result | None = Tournament.results.get_big_bass_winner(tmnt=.tmnt)
#     assert bb_winner is not None
#     assert Decimal("5") == bb_winner.big_bass_weight
#     assert bb_winner.angler.is_member


# # def test_penalty_wt_calculation(, result: Result) -> None:
# #     tournament = Tournament.objects.create(**.indiv)
# #     angler = create_angler()
# #     data = {
# #         "angler": angler,
# #         "num_fish": 5,
# #         "tournament": tournament,
# #         "total_weight": Decimal("10"),
# #         "num_fish_dead": 5,
# #     }
# #     Result.objects.create(**data)
# #     actual = Result.objects.get(tournament=tournament, angler=angler).total_weight
# #     expected = Decimal("8.75")
# #     .assertEqual(expected, actual)

# def test_dq_with_points() -> None:
#     ...

# def test_point_calc() -> None:
#     ...

# def test_place_calc() -> None:
#     ...

# def test_team_result_math() -> None:
#     ...

# def test_team_result_name() -> None:
#     ...

# def test_team_result_dq() -> None:
#     ...
