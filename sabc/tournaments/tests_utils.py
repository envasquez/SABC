"""Utilities used for aiding in unit tests"""
from random import choices, randint, uniform

from names import get_first_name, get_last_name

from django.contrib.auth.models import User

from users.models import Angler

from .models import Result


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
