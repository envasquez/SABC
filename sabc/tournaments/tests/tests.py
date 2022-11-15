# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from decimal import Decimal
from random import choice

import inflect

from django.test import TestCase
from django.contrib.auth.models import User

from .. import LAKES, get_length_from_weight, get_weight_from_length
from ..models import TeamResult, Tournament, Result

from . import (
    create_angler,
    LENGTH_TO_WEIGHT,
    WEIGHT_TO_LENGTH,
    RESULTS_NO_TIE,
    RESULTS_TIE_BB_WINS,
    TEAM_RESULTS_NO_TIE,
)


class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    * AoY points calculations work
    * Payout calculations work
    - Calculating the winner of the Big Bass award works
    - Calculating the winner of a Team tournament works
    * Conversions for weight->length & length->weight are accurate/correct
    """

    def setUp(self):
        """Pre-test set up"""
        lakes = [(l[0], l[1]) for l in LAKES if l[0] != "tbd" and l[1] != "TBD"]
        self.team = {"team": True, "lake": choice(lakes)[1]}
        self.indiv = {"team": False, "lake": choice(lakes)[1]}
        self.paper = {
            "team": False,
            "lake": choice(lakes)[1],
            "paper": True,
        }

    def test_get_weight_by_length(self):
        """Tests that the get_weight_by_length algorithm is accurate

        Test min/max and most common length/weight combos
        """
        for length, expected_weight in LENGTH_TO_WEIGHT:
            self.assertEqual(expected_weight, get_weight_from_length(length))

    def test_get_length_by_weight(self):
        """Tests that the get_length_by_weight algorithm is accurate

        Test min/max and most common length/weight combos
        """
        for weight, expected_length in WEIGHT_TO_LENGTH:
            self.assertEqual(expected_length, get_length_from_weight(weight))

    def test_penalty_weight(self):
        """Test that the penalty weight per dead fish is accurate"""
        tournament = Tournament.objects.create(**self.indiv)
        angler = create_angler()
        data = {
            "angler": angler,
            "num_fish": 5,
            "tournament": tournament,
            "total_weight": Decimal("10"),
            "num_fish_dead": 5,
        }
        Result.objects.create(**data)

        actual = Result.objects.get(tournament=tournament, angler=angler).total_weight
        expected = Decimal("8.75")
        self.assertEqual(expected, actual)

    def test_no_guests_points(self):
        """Test setting places for all members, no guests with points"""
        tournament = Tournament.objects.create(**self.indiv)
        for data in RESULTS_NO_TIE.values():
            angler = create_angler(data["first_name"], data["last_name"], "member")
            if data.get("buy_in"):
                Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
                continue
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data["num_fish"],
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )
        Tournament.results.set_points(tournament)

        pts = 0
        query = {"tournament": tournament, "num_fish__gt": 0}
        for result in Result.objects.filter(**query).order_by("place_finish"):
            result = Result.objects.get(tournament=tournament, place_finish=result.place_finish)
            self.assertEqual(RESULTS_NO_TIE[result.place_finish]["points"], result.points)
            pts = result.points
        query = {"tournament": tournament, "num_fish": 0, "buy_in": False}
        for result in Result.objects.filter(**query):
            self.assertEqual(result.points, pts - 2)
        query = {"tournament": tournament, "buy_in": True}
        for result in Result.objects.filter(**query):
            self.assertEqual(result.points, pts - 4)

    def test_no_guest_no_points(self):
        """Test setting places for all members, no guests with no points"""
        tournament = Tournament.objects.create(**self.indiv)
        tournament.points = False
        tournament.save()
        for data in RESULTS_NO_TIE.values():
            if data.get("buy_in"):
                continue
            angler = create_angler(data["first_name"], data["last_name"], "member")
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data["num_fish"],
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )

        Tournament.results.set_places(tournament)
        query = Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
            "place_finish"
        )
        for result in query:
            self.assertEqual(
                RESULTS_NO_TIE[result.place_finish]["first_name"],
                User.objects.get(pk=result.angler_id).get_short_name(),
            )
            self.assertEqual(0, result.points)

    def test_all_guest_no_points(self):
        """Tests that no points are awarded when points=False"""
        tournament = Tournament.objects.create(**self.indiv)
        tournament.points = False
        tournament.save()

        for data in RESULTS_NO_TIE.values():
            if data.get("buy_in"):  # Guests don't buy-in
                continue
            angler = create_angler(data["first_name"], data["last_name"], "guest")
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data["num_fish"],
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )

        Tournament.results.set_points(tournament)
        for result in Result.objects.filter(tournament=tournament).order_by("place_finish"):
            if result.buy_in:
                continue
            self.assertEqual(0, result.points)

    def test_bb_indiv(self):
        """Tests that BB wins in a tie"""
        tournament = Tournament.objects.create(**self.indiv)
        for data in RESULTS_TIE_BB_WINS.values():
            angler = create_angler(data["first_name"], data["last_name"])
            Result.objects.create(
                angler=angler,
                num_fish=data["num_fish"],
                tournament=tournament,
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data["big_bass_weight"],
            )
        Tournament.results.set_places(tournament)
        self.assertEqual(
            Tournament.results.get_big_bass_winner(tournament),
            Result.objects.get(tournament=tournament, place_finish=1),
        )

    def test_guest_doesnt_win_bb(self):
        """Tests that a guest cannot win big bass"""
        tournament = Tournament.objects.create(**self.indiv)
        for idx, data in RESULTS_TIE_BB_WINS.items():
            member_type = "member" if idx != 2 else "guest"
            Result.objects.create(
                angler=create_angler(data["first_name"], data["last_name"], member_type),
                num_fish=data["num_fish"],
                tournament=tournament,
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data["big_bass_weight"],
            )
        Tournament.results.set_places(tournament)
        bb_winner = Tournament.results.get_big_bass_winner(tournament)
        second_place = Result.objects.get(tournament=tournament, place_finish=2)
        self.assertEqual(bb_winner, second_place)
        self.assertNotEqual(bb_winner.angler.type, "guest")

    # pylint: disable=invalid-name
    def test_bb_team(self):
        """Tests the Big Bass winner function for a team tournament"""
        p = inflect.engine()
        tournament = Tournament.objects.create(**self.team)
        for idx, data in TEAM_RESULTS_NO_TIE.items():
            one = {
                "tournament": tournament,
                "angler": create_angler(
                    first_name=f"{p.number_to_words(p.ordinal(idx)).capitalize()}",
                    last_name="Boater",
                ),
            } | data["result_1"]
            two = {
                "tournament": tournament,
                "angler": create_angler(
                    first_name=f"{p.number_to_words(p.ordinal(idx)).capitalize()} Place",
                    last_name="Partner",
                ),
            } | data["result_2"]
            result_1 = Result.objects.create(**one)
            result_2 = Result.objects.create(**two)
            TeamResult.objects.create(
                **{"result_1": result_1, "result_2": result_2, "tournament": tournament}
            )
        Tournament.results.set_places(tournament)
        bb_winner = Tournament.results.get_big_bass_winner(tournament)
        self.assertEqual(bb_winner.total_weight, Decimal("25"))
        self.assertEqual(bb_winner.big_bass_weight, Decimal("5"))

    def test_get_payouts_indiv(self):
        """Tests the get_payouts function: funds are calculated properly"""
        tournament = Tournament.objects.create(**self.indiv)
        for data in RESULTS_NO_TIE.values():
            angler = create_angler(data["first_name"], data["last_name"], "member")
            if data.get("buy_in"):
                Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
                continue
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data.get("num_fish", 0),
                total_weight=data.get("total_weight", 0),
                num_fish_dead=data.get("num_fish_dead", 0),
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )
        Tournament.results.set_places(tournament)
        payouts = Tournament.results.get_payouts(tournament)
        yes_bb = Result.objects.filter(tournament=tournament, big_bass_weight__gte=5.0).count() > 0
        self.assertEqual(payouts["club"], Decimal("45"))
        self.assertEqual(payouts["total"], Decimal("300"))
        self.assertEqual(payouts["place_1"], Decimal("90"))
        self.assertEqual(payouts["place_2"], Decimal("60"))
        self.assertEqual(payouts["place_3"], Decimal("45"))
        self.assertEqual(payouts["charity"], Decimal("30"))
        self.assertEqual(payouts["bb_carry_over"], not yes_bb)

    def test_guest_every_other_place_points(self):
        """Tests that points are adjusted for guests in ever other place"""
        tournament = Tournament.objects.create(**self.indiv)
        for idx, data in RESULTS_NO_TIE.items():
            member = "guest" if idx % 2 == 0 else "member"
            angler = create_angler(data["first_name"], data["last_name"], member)
            if data.get("buy_in"):
                Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
                continue
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data["num_fish"],
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )
        Tournament.results.set_points(tournament)

        query = Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
            "place_finish"
        )
        points = tournament.max_points
        for result in query:
            result = Result.objects.get(tournament=tournament, place_finish=result.place_finish)
            if result.place_finish % 2 == 0:
                self.assertEqual(result.points, 0)
                continue
            self.assertEqual(points, result.points)
            points -= 1

    def test_guest_top_3_points(self):
        """Tests that points are adjusted for guests winning the top 3 places"""
        tournament = Tournament.objects.create(**self.indiv)
        for idx, data in RESULTS_NO_TIE.items():
            member_type = "guest" if idx <= 3 else "member"
            angler = create_angler(data["first_name"], data["last_name"], member_type)
            if data.get("buy_in"):
                Result.objects.create(tournament=tournament, angler=angler, buy_in=True)
                continue
            Result.objects.create(
                tournament=tournament,
                angler=angler,
                num_fish=data["num_fish"],
                total_weight=data["total_weight"],
                num_fish_dead=data["num_fish_dead"],
                big_bass_weight=data.get("big_bass_weight", Decimal("0")),
            )
        Tournament.results.set_points(tournament)
        points = tournament.max_points
        for result in Result.objects.filter(tournament=tournament, num_fish__gt=0).order_by(
            "place_finish"
        ):
            if result.place_finish <= 3:
                self.assertEqual(result.points, 0)
                continue
            self.assertEqual(result.points, points)
            points -= 1
