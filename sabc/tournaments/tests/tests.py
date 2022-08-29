# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from random import choice
from django.test import TestCase

from .. import LAKES
from ..models import MultidayResult, Tournament, Result

from . import generate_tournament_results, create_tie


class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    - AoY points calculations work
    - Payout calculations work
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

    def test_get_payouts(self):
        """Tests the get_payouts function: funds are calculated properly"""
