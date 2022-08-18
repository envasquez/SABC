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
from random import choices, randint, uniform

from names import get_first_name, get_last_name

from django.test import TestCase

from django.contrib.auth.models import User

from users.models import Angler

from .models import Result


from . import get_length_from_weight, get_weight_from_length


def create_random_angler():
    """Creates an Angler object, that is of member status"""
    first_name = get_first_name()
    last_name = get_last_name()
    user = User.objects.create(
        username=first_name[0].lower() + last_name.lower(),
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name}.{last_name}@gmail.com",
    )
    angler = Angler.objects.get(user=user)
    angler.phone_number = "+15121234567"
    angler.type = "member"
    angler.save()

    return angler


def generate_tournament_results(tournament, num_results=10, num_buy_ins=2):
    """Create 10 result objects in the database and associate it to the given tournament"""

    for _ in range(num_results - num_buy_ins):
        num_fish_weighed = choices(
            [0, 1, 2, 3, 4, 5],
            [0.25, 0.15, 0.10, 0.25, 0.20, 0.05],
            k=1,
        )[0]
        num_fish_dead = randint(0, num_fish_weighed) if num_fish_weighed > 0 else 0
        num_fish_alive = num_fish_weighed - num_fish_dead if num_fish_weighed > 0 else 0
        kwargs = {
            "angler": create_random_angler(),
            "tournament": tournament,
            "buy_in": False,
            "num_fish_weighed": num_fish_weighed,
            "num_fish_dead": num_fish_dead,
            "num_fish_alive": num_fish_alive,
            # 0.87 would be the smallest "legal" fish - a 12" Guadalupe Bass
            "fish_1_wt": round(uniform(0.87, 21.0), 2) if num_fish_weighed >= 1 else 0.0,
            "fish_2_wt": round(uniform(0.87, 21.0), 2) if num_fish_weighed >= 2 else 0.0,
            "fish_3_wt": round(uniform(0.87, 21.0), 2) if num_fish_weighed >= 3 else 0.0,
            "fish_4_wt": round(uniform(0.87, 21.0), 2) if num_fish_weighed >= 4 else 0.0,
            "fish_5_wt": round(uniform(0.87, 21.0), 2) if num_fish_weighed >= 5 else 0.0,
        }
        Result.objects.create(**kwargs)

    for _ in range(num_buy_ins):
        Result.objects.create(
            **{
                "angler": create_random_angler(),
                "tournament": tournament,
                "buy_in": True,
            }
        )


class TestTournaments(TestCase):
    """Tests the formulas for calculations are accurate/correct

    Some Tournament Variations:
        - tournaments with 1 angler - 10000 anlgers
        - 1 team - no teams - all teams
        - some buy-ins, all buy-in, no buy-ins
        - no fish to weigh in, all limits, no limits, some dead fish penalties
        - multi-day tournaments
    """

    def test_single_day_indiv_tournament(self):
        """Tests who are the winners from a tournament:
        team = False
        points = True
        complete = True
        multi_day = False
        """

    def test_tounament_winner_multiday(self):
        """Tests calculating the winner from a tounament"""

    def test_aoy_points(self):
        """Tests points calculation from 1-last place are accurate"""

    def test_big_bass_winner(self):
        """Tests that big bass winner calculation is correct"""

    def test_payouts(self):
        """Tests that the payout calculations are correct"""

    def test_get_weight_by_length(self):
        """Tests that the get_weight_by_length algorithm is accurate

        Test min/max and most common length/weight combos
        """
        for length, expected_weight in [
            (29.875, 17.50),
            (12.0, 0.87),
            (0.25, 0.00),
            (30.00, 18.0),
            (14.00, 1.45),
            (14.50, 1.63),
            (14.75, 1.72),
            (14.375, 1.58),
            (15.00, 1.82),
            (15.25, 1.92),
            (15.625, 2.08),
            (16.875, 2.68),
            (17.75, 3.16),
        ]:
            self.assertEqual(expected_weight, get_weight_from_length(length))

    def test_get_length_by_weight(self):
        """Tests that teh get_length_by_weight algorithm is accurate

        Test min/max and most common length/weight combos
        """
        for weight, expected_length in [
            (1.46, 14.00),
            (11.85, 26.50),
            (0.12, 0.00),
            (0.00, 0),
            (17.27, 29.75),
            (18.00, 30.00),
            (200.00, 30.00),
            (1.75, 14.875),
            (2.00, 15.50),
            (3.56, 18.375),
            (4.12, 19.25),
            (2.66, 16.875),
            (2.83, 17.125),
            (2.57, 16.625),
        ]:
            self.assertEqual(expected_length, get_length_from_weight(weight))


# TPW Length-weight Conversion Table for Texas Largemouth Bass
# https://tpwd.texas.gov/fishboat/fish/recreational/catchrelease/bass_length_weight.phtml
#
# Inches	Fractions
#  	       0	 1/8	 1/4	 3/8	 1/2	 5/8	 3/4	 7/8
# 10	0.48	0.50	0.52	0.54	0.56	0.58	0.61	0.63
# 11	0.66	0.68	0.71	0.73	0.76	0.79	0.81	0.84
# 12	0.87	0.90	0.93	0.97	1.00	1.03	1.07	1.10
# 13	1.14	1.17	1.21	1.25	1.29	1.32	1.37	1.41
# 14	1.45	1.49	1.54	1.58	1.63	1.67	1.72	1.77
# 15	1.82	1.87	1.92	1.97	2.02	2.08	2.13	2.19
# 16	2.25	2.31	2.36	2.42	2.49	2.55	2.61	2.68
# 17	2.74	2.81	2.88	2.95	3.02	3.09	3.16	3.23
# 18	3.31	3.39	3.46	3.54	3.62	3.70	3.78	3.87
# 19	3.95	4.04	4.13	4.22	4.31	4.40	4.49	4.58
# 20	4.68	4.78	4.87	4.97	5.08	5.18	5.28	5.39
# 21	5.49	5.60	5.71	5.82	5.94	6.05	6.17	6.28
# 22	6.40	6.52	6.64	6.77	6.89	7.02	7.15	7.28
# 23	7.41	7.54	7.68	7.81	7.95	8.09	8.23	8.38
# 24	8.52	8.67	8.82	8.97	9.12	9.27	9.43	9.59
# 25	9.75	9.91	10.07	10.23	10.40	10.57	10.74	10.91
# 26	11.09	11.26	11.44	11.62	11.80	11.99	12.17	12.36
# 27	12.55	12.74	12.94	13.13	13.33	13.53	13.73	13.94
# 28	14.15	14.35	14.56	14.78	14.99	15.21	15.43	15.65
# 29	15.87	16.10	16.33	16.56	16.79	17.03	17.26	17.50
