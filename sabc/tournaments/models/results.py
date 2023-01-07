# -*- coding: utf-8 -*-
from decimal import Decimal

from django.apps import apps
from django.urls import reverse
from django.db.models import (
    Model,
    PROTECT,
    CharField,
    ForeignKey,
    BooleanField,
    DecimalField,
    SmallIntegerField,
)


class Result(Model):
    angler = ForeignKey("users.Angler", on_delete=PROTECT)
    buy_in = BooleanField(default=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    num_fish = SmallIntegerField(default=0)
    dq_points = BooleanField(default=False)
    tournament = ForeignKey("tournaments.Tournament", on_delete=PROTECT, null=False, blank=False)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
    disqualified = BooleanField(default=False)
    num_fish_dead = SmallIntegerField(default=0)
    num_fish_alive = SmallIntegerField(default=0, null=True, blank=True)
    penalty_weight = DecimalField(
        default=Decimal("0"), null=True, blank=True, max_digits=5, decimal_places=2
    )
    big_bass_weight = DecimalField(
        default=Decimal("0"), null=True, blank=True, max_digits=5, decimal_places=2
    )

    class Meta:
        ordering = ("place_finish", "-total_weight", "-big_bass_weight")

    def __str__(self):
        place = f"{self.place_finish}."
        weight = f"{self.num_fish} @ {self.total_weight}lbs"
        points = f"{self.points} Points"
        if self.buy_in:
            weight = "Buy-in"
            big_bass = ""
        big_bass = f"{self.big_bass_weight}lb BB"
        return (
            f"{place}{self.angler}{' ' * (30 - len(str(self.angler)))}"
            f"{weight}\t{big_bass}\t{points}\t{self.tournament.name}"
        )

    def get_absolute_url(self):
        return reverse("result-create", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        if self.buy_in:
            self.num_fish = 0
            self.num_fish_dead = 0
            self.total_weight = Decimal("0")
            self.num_fish_alive = 0
            self.penalty_weight = Decimal("0")
            self.big_bass_weight = Decimal("0")

        self.big_bass_weight = self.big_bass_weight
        self.penalty_weight = self.num_fish_dead * self.tournament.rules.dead_fish_penalty
        self.num_fish_alive = self.num_fish - self.num_fish_dead
        if self._state.adding:
            self.total_weight = self.total_weight - self.penalty_weight
        super().save(*args, **kwargs)


class TeamResult(Model):  # pylint: disable=too-many-instance-attributes
    result_1 = ForeignKey(Result, on_delete=PROTECT)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=PROTECT)
    tournament = ForeignKey("tournaments.Tournament", on_delete=PROTECT)

    buy_in = BooleanField(default=False, null=True, blank=True)
    num_fish = SmallIntegerField(default=0, null=True, blank=True)
    team_name = CharField(default="", max_length=1024, null=True, blank=True)
    place_finish = SmallIntegerField(default=0, null=True, blank=True)
    disqualified = BooleanField(default=False)
    total_weight = DecimalField(
        default=Decimal("0"), max_digits=5, decimal_places=2, null=True, blank=True
    )
    num_fish_dead = SmallIntegerField(default=0, null=True, blank=True)
    num_fish_alive = SmallIntegerField(default=0, null=True, blank=True)
    penalty_weight = DecimalField(
        default=Decimal("0"), max_digits=5, decimal_places=2, null=True, blank=True
    )
    big_bass_weight = DecimalField(
        default=Decimal("0"), max_digits=5, decimal_places=2, null=True, blank=True
    )

    def __str__(self):
        name = self.get_team_name()
        place = f"{self.place_finish}."
        weight = f"{self.num_fish} @ {self.total_weight}lbs"
        big_bass = f"{self.big_bass_weight}lb BB"
        return f"{place}{name}{' ' * (60 - len(str(name)))}{weight}\t\t{big_bass}"

    def get_absolute_url(self):
        return reverse("team-create", kwargs={"pk": self.tournament.id})

    def get_team_name(self):
        name = f"{self.result_1.angler.user.get_full_name()}"
        if not self.result_2:
            return f"{name} - solo"
        return f"{name} & {self.result_2.angler.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if self.result_2:
            self.num_fish = self.result_1.num_fish + self.result_2.num_fish
            self.total_weight = self.result_1.total_weight + self.result_2.total_weight
            self.num_fish_dead = self.result_1.num_fish + self.result_2.num_fish_dead
            self.penalty_weight = self.result_1.penalty_weight + self.result_2.penalty_weight
            self.num_fish_alive = self.result_1.num_fish_alive + self.result_2.num_fish_alive
            self.big_bass_weight = max(self.result_1.big_bass_weight, self.result_2.big_bass_weight)
        else:
            for attr in [
                "buy_in",
                "num_fish",
                "total_weight",
                "big_bass_weight",
                "num_fish_alive",
                "num_fish_dead",
                "penalty_weight",
            ]:
                setattr(self, attr, getattr(self.result_1, attr))
        if any([self.result_1.disqualified, self.result_2.disqualified]):
            self.disqualified = True
        self.team_name = self.get_team_name()
        super().save(*args, **kwargs)
