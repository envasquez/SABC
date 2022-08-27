# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from django.test import TestCase

from sabc.tournaments.models import Tournament, Result

from .. import get_length_from_weight, get_weight_from_length

from . import (
    LENGTH_TO_WEIGHT,
    WEIGHT_TO_LENGTH,
    create_tie,
    generate_tournament_results,
)


class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    * Conversions for weight->length & length->weight are accurate/correct
    - AoY points calculations work
    - Payout calculations work
    - Calculating the winner of the Big Bass award works
    - Calculating the winner of a Team tournament works
    - Calculating the winner of a Team multi-day tournament works
    """

    def setUp(self):
        """Pre-test set up"""
        self.multi_day_team = {"team": True, "multi_day": True}
        self.single_day_team = {"team": True, "multi_day": False}
        self.multi_day_indiv = {"team": False, "multi_day": True}
        self.single_day_indiv = {"team": False, "multi_day": False}

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

    def test_indiv_1day_bb_wins_tie(self):
        """Tests that the angler with the biggest bass wins on a single day tournament"""
        tournament = Tournament.objects.create(self.single_day_indiv)

    def test_indiv_1day_most_fish_wins_tie(self):
        """Tests that the angler with the most fish weighed wins on a single day tournament"""
        tournament = Tournament.objects.create(self.single_day_indiv)
        generate_tournament_results(tournament, num_results=5, num_buy_ins=0, multi_day=False)
        highest_wt = max([r.total_weight for r in Result.objects.filter(tournament)])
        winners = create_tie(tournament, total_wieght=highest_wt * 2, win_by="big_bass")

    def test_set_aoy_points(self):
        """Tests that AoY points are set properly"""
        tournament = Tournament.objects.create(self.single_day_indiv)
        generate_tournament_results(tournament, num_results=5, num_buy_ins=0, multi_day=False)
        highest_wt = max([r.total_weight for r in Result.objects.filter(tournament)])
        winners = create_tie(tournament, total_wieght=highest_wt * 2, win_by="big_bass")

    def test_get_payouts(self):
        """Tests the get_payouts function: funds are calculated properly"""
        pass
