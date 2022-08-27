# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.
"""
from django.test import TestCase

from .. import get_length_from_weight, get_weight_from_length

# from ..models import MultidayResult, Tournament, Result
# from ..exceptions import TournamentNotComplete, IncorrectTournamentType


from . import (
    LENGTH_TO_WEIGHT,
    WEIGHT_TO_LENGTH,
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
        pass

    def test_indiv_1day_most_fish_wins_tie(self):
        """Tests that the angler with the most fish weighed wins on a single day tournament"""
        pass

    def test_set_aoy_points(self):
        """Tests that AoY points are set properly"""
        pass

    def test_get_payouts(self):
        """Tests the get_payouts function: funds are calculated properly"""
        pass
