# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from decimal import Decimal
from random import choice, randint
from django.test import TestCase

from .. import LAKES, get_length_from_weight, get_weight_from_length
from ..models import MultidayResult, MultidayTeamResult, TeamResult, Tournament, Result

from . import generate_tournament_results, create_tie, LENGTH_TO_WEIGHT, WEIGHT_TO_LENGTH

# pylint: disable=too-many-public-methods
class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    * AoY points calculations work
    * Payout calculations work
    - Calculating the winner of the Big Bass award works
    * Calculating the winner of a Individual tournament works (single & multi-day)
    - Calculating the winner of a Team tournament works
    - Calculating the winner of a Team multi-day tournament works
    * Conversions for weight->length & length->weight are accurate/correct
    """

    def setUp(self):
        """Pre-test set up"""
        lakes = [(l[0], l[1]) for l in LAKES if l[0] != "tbd" and l[1] != "TBD"]
        self.multi_day_team = {"team": True, "multi_day": True, "lake": choice(lakes)[1]}
        self.single_day_team = {"team": True, "multi_day": False, "lake": choice(lakes)[1]}
        self.multi_day_indiv = {"team": False, "multi_day": True, "lake": choice(lakes)[1]}
        self.single_day_indiv = {"team": False, "multi_day": False, "lake": choice(lakes)[1]}
        self.num_results = randint(25, 250)
        self.num_buy_ins = randint(2, 15)

    def test_set_places_indiv_single_day(self):
        """Tests the set_places() function: Single Day Individual Tournament"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=25, num_buy_ins=3)
        Tournament.results.set_places(tournament)
        results = Result.objects.filter(tournament=tournament).order_by("place_finish")
        for idx, result in enumerate(results, start=1):
            self.assertLessEqual(result.total_weight, results[idx - 1].total_weight)
            self.assertGreaterEqual(result.place_finish, results[idx - 1].place_finish)

    def test_set_places_indiv_multi_day(self):
        """Tests the set_places() function: Multi Day Individual Tournament"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, num_results=25, num_buy_ins=3)
        Tournament.results.set_places(tournament)
        results = MultidayResult.objects.filter(tournament=tournament).order_by("place_finish")
        for idx, result in enumerate(results, start=1):
            self.assertLessEqual(result.total_weight, results[idx - 1].total_weight)
            self.assertGreaterEqual(result.place_finish, results[idx - 1].place_finish)

    def test_set_places_team_single_day(self):
        """Tests the set_places() function: Single Day Team Tournament"""
        tournament = Tournament.objects.create(**self.single_day_team)
        generate_tournament_results(tournament, num_results=25, num_buy_ins=3)
        Tournament.results.set_places(tournament)
        results = TeamResult.objects.filter(tournament=tournament).order_by("place_finish")
        for idx, result in enumerate(results, start=1):
            self.assertLessEqual(result.total_weight, results[idx - 1].total_weight)
            self.assertGreaterEqual(result.place_finish, results[idx - 1].place_finish)

    def test_set_places_team_multi_day(self):
        """Tests the set_places() function: Multi Day Team Tournament"""
        tournament = Tournament.objects.create(**self.multi_day_team)
        generate_tournament_results(tournament, num_results=25, num_buy_ins=3)
        Tournament.results.set_places(tournament)
        results = MultidayTeamResult.objects.filter(tournament=tournament).order_by("place_finish")
        for idx, result in enumerate(results, start=1):
            self.assertLessEqual(result.total_weight, results[idx - 1].total_weight)
            self.assertGreaterEqual(result.place_finish, results[idx - 1].place_finish)

    def test_indiv_bb_wins_tie(self):
        """Tests that the angler with the biggest bass wins on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins)
        create_tie(tournament, win_by="BB", multi_day=False)
        Tournament.results.set_places(tournament)
        # They should have the same total weight
        self.assertEqual(
            Result.objects.get(tournament=tournament, place_finish=1).total_weight,
            Result.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        # Second place should have a smaller big bass
        self.assertLess(
            Result.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
            Result.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
        )

    def test_indiv_most_fish_wins_tie(self):
        """Tests that the angler with the most fish weighed wins on a single day tiebreaker"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins)
        create_tie(tournament, win_by="MOST_FISH")
        Tournament.results.set_places(tournament)
        # They should have the same total weight
        self.assertEqual(
            Result.objects.get(tournament=tournament, place_finish=1).total_weight,
            Result.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        # They should have the same big bass weight
        self.assertEqual(
            Result.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
            Result.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
        )
        # First place should have more num_fish
        self.assertLess(
            Result.objects.get(tournament=tournament, place_finish=2).num_fish,
            Result.objects.get(tournament=tournament, place_finish=1).num_fish,
        )

    def test_indiv_bb_wins_tie_multi_day(self):
        """Tests that the angler with the biggest fish weighed wins on a multi day tiebreaker"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, multi_day=True)
        create_tie(tournament, win_by="BB", multi_day=True)
        Tournament.results.set_places(tournament)
        # They should have the same total weight
        self.assertEqual(
            MultidayResult.objects.get(tournament=tournament, place_finish=1).total_weight,
            MultidayResult.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        # Second place should have a smaller big bass
        self.assertLess(
            MultidayResult.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
            MultidayResult.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
        )

    def test_indiv_most_fish_wins_tie_multi_day(self):
        """Tests that the angler with the biggest fish weighed wins on a multi-day tiebreaker"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, multi_day=True)
        create_tie(tournament, win_by="MOST_FISH", multi_day=True)
        Tournament.results.set_places(tournament)
        # They should have the same total weight
        self.assertEqual(
            MultidayResult.objects.get(tournament=tournament, place_finish=1).total_weight,
            MultidayResult.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        # They should have the same big bass weight
        self.assertEqual(
            MultidayResult.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
            MultidayResult.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
        )
        # First place should have more num_fish
        self.assertLess(
            MultidayResult.objects.get(tournament=tournament, place_finish=2).num_fish,
            MultidayResult.objects.get(tournament=tournament, place_finish=1).num_fish,
        )

    def test_indiv_bb_winner(self):
        """Tests that an angler with the biggest bass wins big bass on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins)
        # Pick a random result in the Top 3
        Tournament.results.set_places(tournament)
        result = Result.objects.get(tournament=tournament, place_finish=2)
        # Create a big bass larger than our generator would, guarantee this result wins BB
        result.big_bass_weight = Decimal("25.00")
        result.save()
        self.assertEqual(result, Tournament.results.get_big_bass_winner(tournament))

    def test_indiv_bb_winner_multi_day(self):
        """Tests that an angler with the largest bass wins big bass on a multi-day tournament"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, multi_day=True)
        Tournament.results.set_places(tournament)
        # Pick the tenth place and modify the result to force a win
        result = MultidayResult.objects.get(tournament=tournament, place_finish=3)
        # Create a big bass larger than our generator would, guarantee this result wins BB
        result.day_1.big_bass_weight = Decimal("25.00")
        result.day_2.big_bass_weight = Decimal("10.00")
        result.save()
        self.assertEqual(result, Tournament.results.get_big_bass_winner(tournament))

    def test_team_bb_winner_single_day(self):
        """Tests that a team with the largest bass wins big on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_team)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, team=True)
        Tournament.results.set_places(tournament)
        result = TeamResult.objects.get(tournament=tournament, place_finish=2)
        result.result_1.big_bass_weight = Decimal("25.00")
        result.save()
        self.assertEqual(Tournament.results.get_big_bass_winner(tournament), result)

    def test_team_bb_wins_tie_single_day(self):
        """Tests that a team with the biggest bass wins a tie breaker on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_team)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, team=True)
        winners = create_tie(tournament, win_by="BB", multi_day=False)
        Tournament.results.set_places(tournament)
        self.assertEqual(winners[0], TeamResult.objects.get(tournament=tournament, place_finish=1))
        self.assertEqual(winners[1], TeamResult.objects.get(tournament=tournament, place_finish=2))

    def test_team_bb_wins_tie_multi_day(self):
        """Tests that a team with the biggest bass wins a tie breaker on a multi-day tournament"""
        tournament = Tournament.objects.create(**self.multi_day_team)
        generate_tournament_results(
            tournament, self.num_results, self.num_buy_ins, multi_day=True, team=True, num_zeros=2
        )
        create_tie(tournament, win_by="BB", multi_day=True)
        Tournament.results.set_places(tournament)
        self.assertEqual(
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=1).total_weight,
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        self.assertGreater(
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
        )

    def test_team_most_fish_wins_tie_single_day(self):
        """Tests that a team with the most fish wins on a tie breaker on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_team)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, team=True)
        create_tie(tournament, win_by="MOST_FISH", multi_day=False)
        Tournament.results.set_places(tournament)
        self.assertEqual(
            TeamResult.objects.get(tournament=tournament, place_finish=1).total_weight,
            TeamResult.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        self.assertEqual(
            TeamResult.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
            TeamResult.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
        )
        self.assertGreater(
            TeamResult.objects.get(tournament=tournament, place_finish=1).num_fish,
            TeamResult.objects.get(tournament=tournament, place_finish=2).num_fish,
        )

    def test_team_most_fish_wins_tie_multi_day(self):
        """Tests that a team with the most fish wins on a tie breaker on a multi day tournament"""
        tournament = Tournament.objects.create(**self.multi_day_team)
        generate_tournament_results(
            tournament, self.num_results, self.num_buy_ins, team=True, multi_day=True
        )
        create_tie(tournament, win_by="MOST_FISH", multi_day=True)
        Tournament.results.set_places(tournament)
        self.assertEqual(
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=1).total_weight,
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=2).total_weight,
        )
        self.assertEqual(
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=1).big_bass_weight,
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=2).big_bass_weight,
        )
        self.assertGreater(
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=1).num_fish,
            MultidayTeamResult.objects.get(tournament=tournament, place_finish=2).num_fish,
        )

    def test_set_aoy_points(self):
        """Tests that AoY points are set properly"""
        self.num_results = 100
        self.num_buy_ins = 5
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, self.num_results, self.num_buy_ins, num_zeros=5)
        Tournament.results.set_aoy_points(tournament)
        lowest_points = (
            Result.objects.filter(
                tournament=tournament,
                day_num=1,
                angler__type="member",
                points__gt=0,
                buy_in=False,
                num_fish__gt=0,
            )
            .order_by("points")
            .first()
            .points
        )
        for result in Result.objects.filter(tournament=tournament).order_by("place_finish"):
            print(result)
            if result.angler.type == "guest":
                self.assertEqual(result.points, 0)
                continue
            if result.num_fish == 0 and not result.buy_in:
                self.assertEqual(lowest_points - 2, result.points)
            if result.buy_in:
                self.assertEqual(lowest_points - 4, result.points)

    def test_get_payouts_indiv(self):
        """Tests the get_payouts function: funds are calculated properly"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=100, num_buy_ins=10, multi_day=False)
        Tournament.results.set_places(tournament)
        payouts = Tournament.results.get_payouts(tournament)
        yes_bb = Result.objects.filter(tournament=tournament, big_bass_weight__gte=5.0).count() > 0
        self.assertEqual(payouts["club"], 300.00)
        self.assertEqual(payouts["total"], 2000.00)
        self.assertEqual(payouts["place_1"], 600.00)
        self.assertEqual(payouts["place_2"], 400.00)
        self.assertEqual(payouts["place_3"], 300.00)
        self.assertEqual(payouts["charity"], 200.00)
        self.assertEqual(payouts["bb_carry_over"], not yes_bb)

    def test_get_payouts_multi_day(self):
        """Tests the get_payouts function: funds are calculated properly for multiday_events"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=100, num_buy_ins=10, multi_day=True)
        Tournament.results.set_places(tournament)
        payouts = Tournament.results.get_payouts(tournament)
        day_1_bb = (
            Result.objects.filter(
                tournament=tournament, day_num=1, big_bass_weight__gte=5.0
            ).count()
            > 0
        )
        day_2_bb = (
            Result.objects.filter(
                tournament=tournament, day_num=2, big_bass_weight__gte=5.0
            ).count()
            > 0
        )
        yes_bb = any([day_1_bb, day_2_bb])
        self.assertEqual(payouts["club"], 600.00)
        self.assertEqual(payouts["total"], 4000.00)
        self.assertEqual(payouts["place_1"], 1200.00)
        self.assertEqual(payouts["place_2"], 800.00)
        self.assertEqual(payouts["place_3"], 600.00)
        self.assertEqual(payouts["charity"], 400.00)
        self.assertEqual(payouts["bb_carry_over"], not yes_bb)

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
