# -*- coding: utf-8 -*-
"""Unittests for Tournaments, Results and TeamResults

The goal is to test the functionality of our models and ensure our formulas work.

1. Create a Tournament
2. Create some results
3. Create some teams
- Have some results buy-in
- Have some results penalize (dead fish)

A. Determine the winner - last place
B. Determine AoY points for 1 - last + buy-ins
C. Determine the largest bass caught
D. Calculate Payout to winners, club and charity
"""
from django.test import TestCase

from .. import get_length_from_weight, get_weight_from_length
from ..models import Tournament, Result
from ..exceptions import TournamentNotComplete


from . import (
    create_tie,
    generate_tournament_results,
    LENGTH_TO_WEIGHT,
    WEIGHT_TO_LENGTH,
)


class TestTournaments(TestCase):
    """Key things about a tournament and its results that we need to test:

    * Conversions for weight->length & length->weight are accurate/correct
    - AoY points calculations work
    - Payout calculations work
    - Calculating the winner of the Big Bass award works
    - Calculating the winner of a multi-day tournament works
    * Calculating the winner of an individual tournament works
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

    def test_incomplete_tournament_fails(self):
        """Ensures you cannot set places for tournaments that are not marked complete"""
        with self.assertRaises(TournamentNotComplete):
            tournament = Tournament.objects.create(**{"complete": False})
            generate_tournament_results(tournament=tournament, num_results=1, num_buy_ins=0)
            Tournament.results.set_individual_places(tournament=tournament)

    def test_set_individual_places_big_bass_wins(self):
        """Tests that set_individual_places sets the proper values when:
        - A tie exists, and one angler has a single bigger bass
        """
        tournament = Tournament.objects.create(**{"complete": True})
        generate_tournament_results(tournament=tournament, num_results=10, num_buy_ins=2)
        target = max(r.total_weight for r in Result.objects.filter(tournament=tournament)) + 2
        winners = create_tie(tournament=tournament, total_weight=target, win_by="big_bass")
        Tournament.results.set_individual_places(tournament=tournament)
        query = Result.objects.filter(tournament=tournament).order_by("place_finish")[:2]
        for idx, result in enumerate(query):
            self.assertEqual(winners[idx].angler, result.angler)

    def test_set_individual_places_most_catches_wins(self):
        """Tests that set_individual_places sets the proper values when:
        - A tie exists, and one angler has the most weighed fish wins (if big bass is the same size)
        """
        tournament = Tournament.objects.create(**{"complete": True})
        generate_tournament_results(tournament=tournament, num_results=10, num_buy_ins=2)
        target = max(r.total_weight for r in Result.objects.filter(tournament=tournament)) + 2
        winners = create_tie(tournament=tournament, total_weight=target, win_by="num_catch")
        Tournament.results.set_individual_places(tournament=tournament)
        query = Result.objects.filter(tournament=tournament).order_by("place_finish")[:2]
        for idx, result in enumerate(query):
            self.assertEqual(winners[idx].angler, result.angler)
