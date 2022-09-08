"""Utilities used for aiding in unit tests

Contains functions to:
- Create random anglers (members)
- Generate random tournament results
- Generate a tie where the winner wins by: big bass and number of weighed fish
"""
from decimal import Decimal

from random import choices, randint, uniform

from names import get_first_name, get_last_name

from django.contrib.auth.models import User

from users.models import Angler

from ..models import MultidayResult, Result

LAKE_BB_SCORES = {
    "LBJ": 5,
    "TRAVIS": 2,
    "BELTON": 3,
    "DECKER": 4,
    "CANYON": 3,
    "MEDINA": 1,
    "AUSTIN": 3,
    "OH-IVIE": 5,
    "BASTROP": 1,
    "FAYETTE": 5,
    "BUCHANAN": 5,
    "PALESTINE": 4,
    "LADY-BIRD": 4,
    "STILLHOUSE": 4,
    "MARBLE-FALLS": 3,
    "RICHLAND-CHAMBERS": 4,
}


def create_random_angler():
    """Creates an Angler object, that is of member status

    Returns:
        An Angler object that was created with random names and other information

    NOTE: Should be pretty safe, the username should have a very low collision rate due to the
    random int selection and first_name char + lastname
    """
    first_name = get_first_name()
    last_name = get_last_name()
    user = User.objects.create(
        username=first_name[0].lower() + last_name.lower() + str(randint(1000, 9999)),
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name}.{last_name}@gmail.com",
    )
    angler = Angler.objects.get(user=user)
    angler.phone_number = "+15121234567"
    angler.type = "member"
    angler.save()

    return angler


def generate_tournament_results(tournament, num_results=10, num_buy_ins=0, multi_day=False):
    """Create Result objects in the database and associate it to the given tournament

    Args:
        tournament (Tournament) The tournament to generate results for
        num_results (int) The number of results to create
        num_buy_ins (int) The number of buy-in results to generate
        multi_day (bool) Create mutli-day results if True single day if False
    NOTE: If multi_day is True, then 2x the amount of results are generated. (day 1 & day 2)
    """

    def _gen_attrs():
        num_fish = choices(
            # An angler can weigh in 0 - 5 legal fish
            [0, 1, 2, 3, 4, 5],
            # Weighted Choices: The % of time an angler weighs in 0 - 5 fish
            # 0 fish 10%, 1 fish 20%, 2 fish 20%, 3 fish 20%, 4 fish 15%, 5 fish 15% = 100%
            [0.10, 0.20, 0.20, 0.20, 0.15, 0.15],
        )[0]
        num_fish_dead = choices(
            # An angler can weigh in 0 - 5 dead fish of legal size
            [0, 1, 2, 3, 4, 5],
            # Weighted Choices: The % of time an angler weighs in 0 - 5 dead fish (5 dead is RARE)
            # 0 fish  55% 1 fish 35% 2 fish 5% 3 fish 3% 4 fish 1% 5 fish 1%
            [0.55, 0.35, 0.05, 0.03, 0.01, 0.01],
        )[0]
        num_fish_alive = num_fish - num_fish_dead if num_fish > 0 else 0
        kwargs = {
            "angler": create_random_angler(),
            "tournament": tournament,
            "buy_in": False,
            "num_fish": num_fish,
            "num_fish_dead": num_fish_dead,
            "num_fish_alive": num_fish_alive,
        }
        tot_wt, bb_wt = 0.0, 0.0
        if LAKE_BB_SCORES[tournament.lake] <= 3:
            tot_wt = uniform(1.5, 14.75)
            bb_wt = 0.0 if tot_wt < 13.50 else uniform(5.0, 9.5)
        elif LAKE_BB_SCORES[tournament.lake] == 4:
            tot_wt = uniform(3.25, 20.0)
            bb_wt = 0.0 if tot_wt < 12.0 else uniform(5.0, 10.5)
        elif LAKE_BB_SCORES[tournament.lake] == 5:
            tot_wt = uniform(3.5, 15.0)
            bb_wt = 0.0 if tot_wt < 10.0 else uniform(5.0, 14.0)
        kwargs["total_weight"] = Decimal(str(tot_wt)) + Decimal(str(bb_wt))
        kwargs["big_bass_weight"] = Decimal(str(bb_wt))

        return kwargs

    #
    # Create random results
    #
    for _ in range(num_results - num_buy_ins):
        attrs = _gen_attrs()
        Result.objects.create(**attrs).save()
        if multi_day:
            angler = attrs["angler"]
            attrs = _gen_attrs()
            attrs["angler"] = angler
            attrs["day_num"] = 2
            Result.objects.create(**attrs).save()
    #
    # Create the buy-ins (if any)
    #
    for _ in range(num_buy_ins):
        attrs = {
            "angler": create_random_angler(),
            "tournament": tournament,
            "buy_in": True,
        }
        Result.objects.create(**attrs).save()
        if multi_day:
            attrs["day_num"] = 2
            Result.objects.create(**attrs).save()


def create_tie(tournament, win_by="BB", multi_day=False):
    """Creates a set of results that are equal in total weight, big_bass, and num_fish_weighed.

    Args:
        tournament (Tournament) The tournament to create a tie for
        win_by (str) The option to win by: "BB" (big bass) otherwise num_weighed_fish wins
        multi_day (bool) Create a multi-day tie
    Returns:
        A QuerySet of results equal to the num_results
        Result QuerySet if not multi_day
        MultiDayResult QuerySet if multi_day

    Chose the first two anglers.
    Create equivalent weight
    Make one have a larger big bass than the other (if win_by=BB)
    Make one have more fish weighed than the other (if not win_by=BB)
    """

    def _create_tie(query):
        """Create tied results based on the win_by strategy"""
        for idx, result in enumerate(query):
            result.num_fish = 5
            if idx == 0 and win_by != "BB":
                result.num_fish = 4
            result.big_bass_weight = Decimal("10.00")
            if idx == 0 and win_by == "BB":
                result.big_bass_weight = Decimal("9.99")
            result.total_weight = Decimal("100.00")
            result.num_fish_dead = 0
            result.penalty_weight = Decimal("0.00")
            result.save()

    #
    # Get the day1 leaders & create a tie, duplicate the results if multi_day
    #
    winners = Result.objects.filter(tournament=tournament, day_num=1)[:2]
    _create_tie(winners)
    if multi_day:
        first = Result.objects.get(tournament=tournament, angler=winners[0].angler, day_num=2)
        second = Result.objects.get(tournament=tournament, angler=winners[1].angler, day_num=2)
        _create_tie([first, second])

    return (
        Result.objects.filter(tournament=tournament, day_num=1)[:2]
        if not multi_day
        else MultidayResult.objects.filter(tournament=tournament)[:2]
    )


# TPW Length-weight Conversion Table for Texas Largemouth Bass
# https://tpwd.texas.gov/fishboat/fish/recreational/catchrelease/bass_length_weight.phtml

# Inches	Fractions
#        0  	 1/8	 1/4	 3/8	 1/2	 5/8	 3/4	 7/8
# ----------------------------------------------------------------
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
LENGTH_TO_WEIGHT = [
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
]
WEIGHT_TO_LENGTH = [
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
]