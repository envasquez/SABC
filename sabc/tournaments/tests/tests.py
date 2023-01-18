# # -*- coding: utf-8 -*-
# from typing import Any

# from decimal import Decimal
# from random import choice
# from pathlib import Path

# from django.test import TestCase
# from django.db.models import QuerySet
# from django.contrib.auth.models import User

# from sabc.settings import STATICFILES_DIRS

# from .. import get_length_from_weight, get_weight_from_length
# from ..models.lakes import Ramp
# from ..models.payouts import PayOutMultipliers
# from ..models.results import Result
# from ..models.tournament import Tournament

# from . import (
#     create_angler,
#     LENGTH_TO_WEIGHT,
#     WEIGHT_TO_LENGTH,
#     RESULTS_NO_TIE,
#     RESULTS_TIE_BB_WINS,
#     load_lakes_from_yaml,
# )

# LAKES_YAML: str = str(Path(STATICFILES_DIRS[0]) / "lakes.yaml")


# class TestTournaments(TestCase):
#     """Key things about a tournament and its results that we need to test:

#     * AoY points calculations work
#     * Payout calculations work
#     - Calculating the winner of the Big Bass award works
#     - Calculating the winner of a Team tournament works
#     * Conversions for weight->length & length->weight are accurate/correct
#     """

#     def setUp(self):
#         """Pre-test set up"""
#         pom: PayOutMultipliers = PayOutMultipliers.objects.create()
#         lake: str = choice(load_lakes_from_yaml(LAKES_YAML))
#         ramp: Ramp = choice(Ramp.objects.filter(lake=lake))
#         self.team: dict[str, Any] = {
#             "team": True,
#             "lake": lake,
#             "ramp": ramp,
#             "payout_multiplier": pom,
#         }
#         self.indiv: dict[str, Any] = {
#             "team": False,
#             "lake": lake,
#             "ramp": ramp,
#             "payout_multiplier": pom,
#         }
#         self.paper: dict[str, Any] = {
#             "team": False,
#             "lake": lake,
#             "ramp": ramp,
#             "paper": True,
#             "payout_multiplier": pom,
#         }

# def test_penalty_weight(self):
#     """Test that the penalty weight per dead fish is accurate"""
#     ...

# def test_no_guests_points(self):
#     """Test setting places for all members, no guests with points"""
#     tournament = Tournament.objects.create(**self.indiv)
#     for data in RESULTS_NO_TIE.values():
#         angler = create_angler(data["first_name"], data["last_name"], "member")
#         if data.get("buy_in"):
#             Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
#             continue
#         Result.objects.create(
#             tournament=tournament,
#             angler=angler,
#             num_fish=data["num_fish"],
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#         )
#     Tournament.results.reconcile_indiv_results(tournament)

#     pts = 0
#     query = {"tournament": tournament, "num_fish__gt": 0}
#     for result in Result.objects.filter(**query).order_by("place_finish"):
#         result = Result.objects.get(tournament=tournament, place_finish=result.place_finish)
#         self.assertEqual(RESULTS_NO_TIE[result.place_finish]["points"], result.points)
#         pts = result.points
#     query = {"tournament": tournament, "num_fish": 0, "buy_in": False}
#     for result in Result.objects.filter(**query):
#         self.assertEqual(result.points, pts - 2)
#     query = {"tournament": tournament, "buy_in": True}
#     for result in Result.objects.filter(**query):
#         self.assertEqual(result.points, pts - 4)

# def test_no_guest_no_points(self):
#     """Test setting places for all members, no guests with no points"""
#     tournament = Tournament.objects.create(**self.indiv)
#     tournament.points = False
#     tournament.save()
#     for data in RESULTS_NO_TIE.values():
#         if data.get("buy_in"):
#             continue
#         angler = create_angler(data["first_name"], data["last_name"], "member")
#         Result.objects.create(
#             tournament=tournament,
#             angler=angler,
#             num_fish=data["num_fish"],
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#         )

#     Tournament.results.reconcile_indiv_results(tournament)
#     query: QuerySet = Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
#         "place_finish"
#     )
#     for result in query:
#         self.assertEqual(
#             RESULTS_NO_TIE[result.place_finish]["first_name"],
#             User.objects.get(pk=result.angler_id).get_short_name(),
#         )
#         self.assertEqual(0, result.points)

# def test_all_guest_no_points(self):
#     """Tests that no points are awarded when points=False"""
#     tournament = Tournament.objects.create(**self.indiv)
#     tournament.points = False
#     tournament.save()

#     for data in RESULTS_NO_TIE.values():
#         if data.get("buy_in"):  # Guests don't buy-in
#             continue
#         angler = create_angler(data["first_name"], data["last_name"], "guest")
#         Result.objects.create(
#             tournament=tournament,
#             angler=angler,
#             num_fish=data["num_fish"],
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#         )

#     Tournament.results.reconcile_indiv_results(tmnt=tournament)
#     for result in Result.objects.filter(tournament=tournament):
#         if result.buy_in:
#             continue
#         self.assertEqual(0, result.points)

# def test_bb_indiv(self):
#     """Tests that BB wins in a tie"""
#     tournament = Tournament.objects.create(**self.indiv)
#     for data in RESULTS_TIE_BB_WINS.values():
#         angler = create_angler(data["first_name"], data["last_name"])
#         Result.objects.create(
#             angler=angler,
#             num_fish=data["num_fish"],
#             tournament=tournament,
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data["big_bass_weight"],
#         )
#     Tournament.results.reconcile_indiv_results(tournament)
#     self.assertEqual(
#         Tournament.results.get_big_bass_winner(tournament),
#         Result.objects.get(tournament=tournament, place_finish=1),
#     )

# def test_guest_doesnt_win_bb(self):
#     """Tests that a guest cannot win big bass"""
#     tournament = Tournament.objects.create(**self.indiv)
#     for idx, data in RESULTS_TIE_BB_WINS.items():
#         member_type = "member" if idx != 2 else "guest"
#         Result.objects.create(
#             angler=create_angler(data["first_name"], data["last_name"], member_type),
#             num_fish=data["num_fish"],
#             tournament=tournament,
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data["big_bass_weight"],
#         )
#     Tournament.results.reconcile_indiv_results(tournament)
#     bb_winner = Tournament.results.get_big_bass_winner(tournament)
#     second_place = Result.objects.get(tournament=tournament, place_finish=2)
#     self.assertEqual(bb_winner, second_place)
#     self.assertNotEqual(bb_winner, None)


# def test_guest_every_other_place_points(self):
#     """Tests that points are adjusted for guests in ever other place"""
#     tournament = Tournament.objects.create(**self.indiv)
#     for idx, data in RESULTS_NO_TIE.items():
#         member = "guest" if idx % 2 == 0 else "member"
#         angler = create_angler(data["first_name"], data["last_name"], member)
#         if data.get("buy_in"):
#             Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
#             continue
#         Result.objects.create(
#             tournament=tournament,
#             angler=angler,
#             num_fish=data["num_fish"],
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#         )
#     Tournament.results.reconcile_indiv_results(tournament)

#     query = Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
#         "place_finish"
#     )
#     points = tournament.max_points
#     for result in query:
#         result = Result.objects.get(tournament=tournament, place_finish=result.place_finish)
#         if result.place_finish % 2 == 0:
#             self.assertEqual(result.points, 0)
#             continue
#         self.assertEqual(points, result.points)
#         points -= 1

# def test_guest_top_3_points(self):
#     """Tests that points are adjusted for guests winning the top 3 places"""
#     tournament = Tournament.objects.create(**self.indiv)
#     for idx, data in RESULTS_NO_TIE.items():
#         member_type = "guest" if idx <= 3 else "member"
#         angler = create_angler(data["first_name"], data["last_name"], member_type)
#         if data.get("buy_in"):
#             Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
#             continue
#         Result.objects.create(
#             tournament=tournament,
#             angler=angler,
#             num_fish=data["num_fish"],
#             total_weight=data["total_weight"],
#             num_fish_dead=data["num_fish_dead"],
#             big_bass_weight=data.get("big_bass_weight", Decimal("0")),
#         )
#     Tournament.results.reconcile_indiv_results(tournament)
#     points = tournament.max_points
#     for result in Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
#         "place_finish"
#     ):
#         if result.place_finish <= 3:
#             self.assertEqual(result.points, 0)
#             continue
#         self.assertEqual(result.points, points)
#         points -= 1
