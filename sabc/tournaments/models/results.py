# -*- coding: utf-8 -*-
from decimal import Decimal

from django.db.models import (
    CASCADE,
    PROTECT,
    BooleanField,
    CharField,
    DecimalField,
    ForeignKey,
    Model,
    SmallIntegerField,
)
from django.urls import reverse


class Result(Model):
    buy_in = BooleanField(default=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    num_fish = SmallIntegerField(default=0)
    dq_points = BooleanField(default=False)
    locked = BooleanField(default=False)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
    disqualified = BooleanField(default=False)
    num_fish_dead = SmallIntegerField(default=0)
    num_fish_alive = SmallIntegerField(default=0, null=True, blank=True)
    penalty_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
    big_bass_weight: DecimalField = DecimalField(
        default=Decimal("0"), max_digits=5, decimal_places=2
    )

    angler: ForeignKey = ForeignKey("users.Angler", on_delete=PROTECT)
    tournament: ForeignKey = ForeignKey(
        "tournaments.Tournament", on_delete=CASCADE, null=False, blank=False
    )

    def __str__(self):
        place = f"{self.place_finish}.{self.angler}"
        weight = f"{self.num_fish} fish for: {self.total_weight}lbs"
        points = f"[{self.points}pts]" if self.tournament.points_count else ""
        if self.buy_in:
            weight = "Buy-in"
        big_bass = (
            f"{self.big_bass_weight}lb BB"
            if not self.buy_in and self.big_bass_weight
            else ""
        )
        return " ".join(
            [s for s in [place, weight, big_bass, self.tournament.name, points] if s]
        )

    def get_absolute_url(self):
        return reverse("result-create", kwargs={"pk": self.tournament.id})

    def save(self, *args, **kwargs):
        if self.buy_in:
            self.num_fish = 0
            self.num_fish_dead = 0
            self.total_weight = Decimal("0")
            self.num_fish_alive = 0
            self.penalty_weight = Decimal("0")
        self.penalty_weight = (
            self.num_fish_dead * self.tournament.rules.dead_fish_penalty
        )
        self.num_fish_alive = self.num_fish - self.num_fish_dead  # type: ignore
        if self._state.adding:
            self.total_weight = self.total_weight - self.penalty_weight
        super().save(*args, **kwargs)


class TeamResult(Model):
    buy_in = BooleanField(default=False, null=True, blank=True)
    num_fish = SmallIntegerField(default=0, null=True, blank=True)
    team_name = CharField(default="", max_length=1024, null=True, blank=True)
    manual_edit = BooleanField(default=False)
    place_finish = SmallIntegerField(default=0, null=True, blank=True)
    disqualified = BooleanField(default=False)
    total_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
    num_fish_dead = SmallIntegerField(default=0, null=True, blank=True)
    num_fish_alive = SmallIntegerField(default=0)
    penalty_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
    big_bass_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)

    result_1 = ForeignKey("tournaments.Result", on_delete=CASCADE)
    result_2 = ForeignKey(
        "tournaments.Result", null=True, blank=True, related_name="+", on_delete=CASCADE
    )
    tournament: ForeignKey = ForeignKey("tournaments.Tournament", on_delete=CASCADE)

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
        use_result_1 = all([not self.result_1.disqualified, not self.result_1.buy_in])
        use_result_2 = all(
            [self.result_2, not self.result_2.disqualified if self.result_2 else False]
        )
        if use_result_1 and use_result_2:
            self.num_fish = sum([self.result_1.num_fish, self.result_2.num_fish])
            self.total_weight = sum(
                [self.result_1.total_weight, self.result_2.total_weight]
            )
            self.num_fish_dead = sum(
                [self.result_1.num_fish, self.result_2.num_fish_dead]
            )
            self.penalty_weight = sum(
                [self.result_1.penalty_weight, self.result_2.penalty_weight]
            )
            self.num_fish_alive = sum(
                [self.result_1.num_fish_alive, self.result_2.num_fish_alive]
            )
            self.big_bass_weight = max(
                self.result_1.big_bass_weight, self.result_2.big_bass_weight
            )
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
                setattr(
                    self,
                    attr,
                    getattr(
                        self.result_1 if use_result_2 is False else self.result_2, attr
                    ),
                )

        if any(
            [
                self.result_1.disqualified,
                self.result_2.disqualified if self.result_2 else False,
            ]
        ):
            self.disqualified = True

        self.team_name = self.get_team_name()
        super().save(*args, **kwargs)
