# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from decimal import Decimal
from random import choice
from django.test import TestCase

from .. import LAKES
from ..models import MultidayResult, Tournament, Result
from ..exceptions import IncorrectTournamentType, TournamentNotComplete

from . import generate_tournament_results, create_tie


class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    * AoY points calculations work
    * Payout calculations work
    - Calculating the winner of the Big Bass award works
    * Calculating the winner of a Individual tournament works (single & multi-day)
    - Calculating the winner of a Team tournament works
    - Calculating the winner of a Team multi-day tournament works
    - Conversions for weight->length & length->weight are accurate/correct
    """

    def setUp(self):
        """Pre-test set up"""
        lakes = [(l[0], l[1]) for l in LAKES if l[0] != "tbd" and l[1] != "TBD"]
        self.multi_day_team = {"team": True, "multi_day": True, "lake": choice(lakes)[1]}
        self.single_day_team = {"team": True, "multi_day": False, "lake": choice(lakes)[1]}
        self.multi_day_indiv = {"team": False, "multi_day": True, "lake": choice(lakes)[1]}
        self.single_day_indiv = {"team": False, "multi_day": False, "lake": choice(lakes)[1]}

    def test_indiv_bb_wins_tie(self):
        """Tests that the angler with the biggest bass wins on a single day tournament"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=10, num_buy_ins=5)
        winners = create_tie(tournament, win_by="BB", multi_day=False)
        Tournament.results.set_individual_places(tournament)
        first = {"tournament": tournament, "place_finish": 1, "day_num": 1}
        second = {"tournament": tournament, "place_finish": 2, "day_num": 1}
        self.assertEqual(winners[0], Result.objects.get(**first))
        self.assertEqual(winners[1], Result.objects.get(**second))

    def test_indiv_most_fish_wins_tie(self):
        """Tests that the angler with the most fish weighed wins on a single day tiebreaker"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=10, num_buy_ins=5)
        winners = create_tie(tournament, win_by="MOST_FISH")
        Tournament.results.set_individual_places(tournament)
        first = {"tournament": tournament, "place_finish": 1, "day_num": 1}
        second = {"tournament": tournament, "place_finish": 2, "day_num": 1}
        self.assertEqual(winners[0], Result.objects.get(**first))
        self.assertEqual(winners[1], Result.objects.get(**second))

    def test_incorrect_tournament_type(self):
        """Tests that an exception is raised when setting individual places on a team tournament"""
        tournament = Tournament.objects.create(**self.single_day_team)
        with self.assertRaises(IncorrectTournamentType):
            Tournament.results.set_individual_places(tournament=tournament)

    def test_indiv_bb_wins_tie_multi_day(self):
        """Tests that the angler with the biggest fish weighed wins on a multi day tiebreaker"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, num_results=20, num_buy_ins=3, multi_day=True)
        winners = create_tie(tournament, win_by="BB", multi_day=True)
        Tournament.results.set_individual_places(tournament)
        first = {"tournament": tournament, "place_finish": 1}
        second = {"tournament": tournament, "place_finish": 2}
        self.assertEqual(winners[0], MultidayResult.objects.get(**first))
        self.assertEqual(winners[1], MultidayResult.objects.get(**second))

    def test_indiv_most_fish_wins_tie_multi_day(self):
        """Tests that the angler with the biggest fish weighed wins on a multi-day tiebreaker"""
        tournament = Tournament.objects.create(**self.multi_day_indiv)
        generate_tournament_results(tournament, num_results=20, num_buy_ins=3, multi_day=True)
        winners = create_tie(tournament, win_by="MOST_FISH", multi_day=True)
        Tournament.results.set_individual_places(tournament)
        first = {"tournament": tournament, "place_finish": 1}
        second = {"tournament": tournament, "place_finish": 2}
        self.assertEqual(winners[0], MultidayResult.objects.get(**first))
        self.assertEqual(winners[1], MultidayResult.objects.get(**second))

    def test_team_bb_wins(self):
        """Tests that a team with the biggest bass wins on a single day tournament"""

    def test_team_most_fish_wins(self):
        """Tests that a team with the most fish wins on a single day tournament tiebreaker"""

    def test_set_aoy_points(self):
        """Tests that AoY points are set properly"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=20, num_buy_ins=5)
        Tournament.results.set_individual_places(tournament)
        Tournament.results.set_aoy_points(tournament)
        for result in Result.objects.filter(tournament=tournament, buy_in=False):
            self.assertEqual(result.points, 100 - (result.place_finish - 1))
        expected = Result.objects.filter(tournament=tournament, buy_in=False).last().points - 2
        for result in Result.objects.filter(tournament=tournament, buy_in=True):
            self.assertEqual(expected, result.points)

    def test_get_payouts_indiv(self):
        """Tests the get_payouts function: funds are calculated properly"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=100, num_buy_ins=10, multi_day=False)
        Tournament.results.set_individual_places(tournament)  # Completes the tournament!
        payouts = Tournament.results.get_payouts(tournament)
        yes_bb = Result.objects.filter(tournament=tournament, big_bass_weight__gte=5.0).count() > 0
        self.assertEqual(payouts["club"], Decimal("300.00"))
        self.assertEqual(payouts["total"], Decimal("2000.00"))
        self.assertEqual(payouts["place_1"], Decimal("600.00"))
        self.assertEqual(payouts["place_2"], Decimal("400.00"))
        self.assertEqual(payouts["place_3"], Decimal("300.00"))
        self.assertEqual(payouts["charity"], Decimal("200.00"))
        self.assertEqual(payouts["bb_carry_over"], not yes_bb)

        tournament.complete = False
        tournament.save()
        with self.assertRaises(TournamentNotComplete):
            Tournament.results.get_payouts(tournament)

    def test_get_payouts_multi_day(self):
        """Tests the get_payouts function: funds are calculated properly for multiday_events"""
        tournament = Tournament.objects.create(**self.single_day_indiv)
        generate_tournament_results(tournament, num_results=100, num_buy_ins=10, multi_day=True)
        Tournament.results.set_individual_places(tournament)  # Completes the tournament!
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
        self.assertEqual(payouts["club"], Decimal("600.00"))
        self.assertEqual(payouts["total"], Decimal("4000.00"))
        self.assertEqual(payouts["place_1"], Decimal("1200.00"))
        self.assertEqual(payouts["place_2"], Decimal("800.00"))
        self.assertEqual(payouts["place_3"], Decimal("600.00"))
        self.assertEqual(payouts["charity"], Decimal("400.00"))
        self.assertEqual(payouts["bb_carry_over"], not yes_bb)
