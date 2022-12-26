# -*- coding: utf-8 -*-
from random import randint
from decimal import Decimal

from yaml import safe_load

from names import get_first_name, get_last_name

from django.contrib.auth.models import User

from users.models import Angler

from tournaments.models import Lake, Ramp


def load_lakes_from_yaml(yaml_file):
    with open(yaml_file, "r", encoding="utf-8") as lakes:
        lakes = safe_load(lakes)
    for lake_name in lakes:
        lake, _ = Lake.objects.get_or_create(name=lake_name)
        for ramp in lakes[lake_name]["ramps"]:
            Ramp.objects.get_or_create(
                lake=lake, name=ramp["name"], google_maps=ramp["google_maps"]
            )
    return Lake.objects.all()


def create_angler(first_name=None, last_name=None, angler_type="member"):
    """Creates an Angler object.

    Args:
        first_name (str) The first name of the angler to create.
        last_name (str) The last name of the angler to create.
        angler_type (str) Angler type - member or guest
    Returns:
        (Angler) An Angler object that was created with random names and other information
    """
    last_name = get_last_name() if not last_name else last_name
    first_name = get_first_name() if not first_name else first_name
    user = User.objects.create(
        username=first_name[0].lower() + last_name.lower() + str(randint(1000, 9999)),
        first_name=first_name,
        last_name=last_name,
        email=f"{first_name}.{last_name}@unittest.com",
    )
    angler = Angler.objects.get(user=user)
    angler.phone_number = f"+{randint(10000000000, 99999999999)}"
    angler.type = angler_type
    angler.save()

    return angler


RESULTS_NO_TIE = {
    1: {
        "first_name": "First",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("21.00"),
        "num_fish_dead": 0,
        "big_bass_weight": Decimal("5.00"),
        "points": 100,
    },
    2: {
        "first_name": "Second",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("20.00"),
        "num_fish_dead": 0,
        "big_bass_weight": Decimal("7.00"),
        "points": 99,
    },
    3: {
        "first_name": "Third",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("19.00"),
        "num_fish_dead": 0,
        "points": 98,
    },
    4: {
        "first_name": "Fourth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("18.00"),
        "num_fish_dead": 0,
        "points": 97,
    },
    5: {
        "first_name": "Fifth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("17.00"),
        "num_fish_dead": 0,
        "points": 96,
    },
    6: {
        "first_name": "Sixth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("16.00"),
        "num_fish_dead": 0,
        "points": 95,
    },
    7: {
        "first_name": "Seventh",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("15.00"),
        "num_fish_dead": 0,
        "points": 94,
    },
    8: {
        "first_name": "Eigth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("14.00"),
        "num_fish_dead": 0,
        "points": 93,
    },
    9: {
        "first_name": "Ninth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("13.00"),
        "num_fish_dead": 0,
        "points": 92,
    },
    10: {
        "first_name": "Tenth",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("12.00"),
        "num_fish_dead": 0,
        "points": 91,
    },
    11: {
        "first_name": "Eleventh",
        "last_name": "Place",
        "num_fish": 0,
        "total_weight": Decimal("0"),
        "num_fish_dead": 0,
        "points": 89,
    },
    12: {
        "first_name": "Twelfth",
        "last_name": "Place",
        "num_fish": 0,
        "total_weight": Decimal("0"),
        "num_fish_dead": 0,
        "points": 89,
    },
    13: {
        "first_name": "Thrteenth",
        "last_name": "Place",
        "num_fish": 0,
        "total_weight": Decimal("0"),
        "num_fish_dead": 0,
        "points": 89,
    },
    14: {
        "first_name": "Fourteenth",
        "last_name": "Place",
        "buy_in": True,
        "points": 87,
    },
    15: {
        "first_name": "Fifteenth",
        "last_name": "Place",
        "buy_in": True,
        "points": 87,
    },
}

RESULTS_TIE_BB_WINS = {
    1: {
        "first_name": "Third",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("21.00"),
        "num_fish_dead": 0,
        "big_bass_weight": Decimal("5.00"),
        "points": 99,
    },
    2: {
        "first_name": "First",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("21.00"),
        "num_fish_dead": 0,
        "big_bass_weight": Decimal("7.00"),
        "points": 100,
    },
    3: {
        "first_name": "Second",
        "last_name": "Place",
        "num_fish": 5,
        "total_weight": Decimal("21.00"),
        "num_fish_dead": 0,
        "big_bass_weight": Decimal("6.00"),
        "points": 98,
    },
}

TEAM_RESULTS_NO_TIE = {
    1: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("25"), "big_bass_weight": Decimal("5")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("24"), "big_bass_weight": Decimal("0")},
    },
    2: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("24"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("23"), "big_bass_weight": Decimal("0")},
    },
    3: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("23"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("22"), "big_bass_weight": Decimal("0")},
    },
    4: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("22"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("21"), "big_bass_weight": Decimal("0")},
    },
    5: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("21"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("20"), "big_bass_weight": Decimal("0")},
    },
    6: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("20"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("19"), "big_bass_weight": Decimal("0")},
    },
    7: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("19"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("18"), "big_bass_weight": Decimal("0")},
    },
    8: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("18"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("17"), "big_bass_weight": Decimal("0")},
    },
    9: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("17"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("16"), "big_bass_weight": Decimal("0")},
    },
    10: {
        "result_1": {"num_fish": 5, "total_weight": Decimal("16"), "big_bass_weight": Decimal("0")},
        "result_2": {"num_fish": 5, "total_weight": Decimal("15"), "big_bass_weight": Decimal("0")},
    },
}

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
