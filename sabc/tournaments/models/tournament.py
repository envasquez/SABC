# -*- coding: utf-8 -*-
# pylint: disable=no-member
import datetime
from decimal import Decimal
from time import strftime
from typing import Any

from django.db.models import (
    PROTECT,
    BooleanField,
    CharField,
    ForeignKey,
    Manager,
    Model,
    QuerySet,
    TextField,
)
from django.urls import reverse

from .. import get_last_sunday
from . import TODAY
from .events import Events
from .payouts import PayOutMultipliers
from .results import Result, TeamResult
from .rules import RuleSet

DEFAULT_FACEBOOK_URL: str = "https://www.facebook.com/SouthAustinBassClub"
DEFAULT_INSTAGRAM_URL: str = "https://www.instagram.com/south_austin_bass_club"


class TournamentManager(Manager):
    def get_last_place(self, tmnt):
        """Returns the last place result number"""
        results = Result.objects.filter(tournament=tmnt).order_by("place_finish")
        if results:
            return results.last().place_finish
        return 1

    def get_last_points(self, tmnt):
        results = Result.filter(tournament=tmnt).order_by("-points")
        if results:
            return results.last().points
        return tmnt.rules.max_points

    def assign_places(self, query: QuerySet, place: int = 1) -> None:
        if query.count() == 0:
            return
        # Ensure ordering ... according to the bylaws
        query.order_by("-total_weight", "-big_bass_weight", "-num_fish")
        prev: Result | None = None
        for place_finish, result in enumerate(query, start=place):
            tie: bool = False
            result.place_finish = place_finish
            if prev:
                tie = result.total_weight == prev.total_weight
                result.place_finish = place_finish if not tie else prev.place_finish
            result.save()
            prev = result

    def set_places(self, tmnt) -> None:
        pass
        # # Set places for non-zeroes and zeroes (calculated)
        # self.assign_places(self.get_non_zeroes(tmnt=tmnt))
        # self.assign_places(self.get_zeroes(tmnt=tmnt), place=self.get_last_place(tmnt=tmnt))
        # # Set places for buy-ins
        # last_place: int = self.get_last_place(tmnt=tmnt)
        # for result in self.get_buy_ins(tmnt=tmnt):
        #     result.place_finish = last_place
        #     result.save()
        # # Set places for DQs (should always be LAST!)
        # last_place = self.get_last_place(tmnt=tmnt) + 1
        # for result in self.get_disqualified(tmnt=tmnt):
        #     result.place_finish = last_place
        #     result.save()
        # # Set team results
        # if tmnt.team:
        #     self.assign_places(TeamResult.objects.filter(tournament=tmnt))

    def set_points(self, tmnt) -> None:
        pass
        # self.set_places(tmnt=tmnt)
        # points: int = tmnt.rules.max_points
        # for result in self.get_non_zeroes(tmnt=tmnt):
        #     if not result.locked:
        #         result.points = points
        #         result.save()
        #         continue
        #     result.points = points if result.member else 0
        #     points -= 1
        # # Zeros receive 2 less points than the last non-zero result
        # last_points: int = self.get_last_points(tmnt=tmnt)
        # for result in self.get_zeroes(tmnt=tmnt):
        #     if result.locked:
        #         continue
        #     result.points = last_points - tmnt.rules.zeroes_points_offest
        #     result.save()
        # # DQs with points receive 3 less points than the last non-zero result
        # last_points = self.get_last_points(tmnt=tmnt)
        # for result in self.get_disqualified(tmnt=tmnt):
        #     if result.locked:
        #         continue
        #     result.points = last_points - tmnt.rules.disqualified_points_offset
        #     result.save()
        # # Buy-ins receive 4 less points than the the last non-zero result
        # last_points = self.get_last_points(tmnt=tmnt)
        # for result in self.get_buy_ins(tmnt=tmnt):
        #     if result.locked:
        #         continue
        #     result.points = last_points - tmnt.rules.buy_ins_points_offset
        #     result.save()

    def get_non_zeroes(self, tmnt) -> QuerySet:
        query: dict[str, Any] = {"tournament": tmnt, "locked": False, "disqualified": False, "num_fish__gt": 0}
        order: tuple[str, str, str] = ("-total_weight", "-big_bass_weight", "-num_fish")
        return Result.objects.filter(**query).order_by(*order)

    def get_zeroes(self, tmnt) -> QuerySet:
        query: dict = {"buy_in": False, "num_fish": 0, "tournament": tmnt, "disqualified": False, "locked": False}
        return Result.objects.filter(**query)

    def get_buy_ins(self, tmnt) -> QuerySet:
        return Result.objects.filter(tournament=tmnt, buy_in=True)

    def get_disqualified(self, tmnt) -> QuerySet:
        order: tuple[str, str, str] = ("-total_weight", "-big_bass_weight", "-num_fish")
        return Result.objects.filter(tournament=tmnt, disqualified=True).order_by(*order)

    def get_big_bass_winner(self, tmnt) -> Result | None:
        query: dict[str, Any] = {"angler__member": True, "tournament": tmnt, "big_bass_weight__gte": Decimal("5")}
        bb_results: QuerySet = Result.objects.filter(**query)
        return bb_results.first() if len(bb_results) == 1 else None

    def get_payouts(self, tmnt) -> dict[str, Decimal | bool]:
        bb_query: dict[str, Any] = {"angler__member": True, "tournament": tmnt, "big_bass_weight__gte": Decimal("5")}
        bb_exists: bool = Result.objects.filter(**bb_query).count() > 0
        num_anglers: int = Result.objects.filter(tournament=tmnt).count()
        pom: PayOutMultipliers = tmnt.payout_multiplier
        return {
            "club": pom.club * num_anglers,
            "total": pom.entry_fee * num_anglers,
            "place_1": pom.place_1 * num_anglers,
            "place_2": pom.place_2 * num_anglers,
            "place_3": pom.place_3 * num_anglers,
            "charity": pom.charity * num_anglers,
            "big_bass": pom.big_bass * num_anglers,
            "bb_carry_over": not bb_exists,
        }


class Tournament(Model):
    lake: ForeignKey = ForeignKey("tournaments.Lake", null=True, blank=True, on_delete=PROTECT)
    ramp: ForeignKey = ForeignKey("tournaments.Ramp", null=True, blank=True, on_delete=PROTECT)
    rules: ForeignKey = ForeignKey("tournaments.RuleSet", null=True, blank=True, on_delete=PROTECT)
    payout_multiplier: ForeignKey = ForeignKey(
        "tournaments.PayOutMultipliers", null=True, blank=True, on_delete=PROTECT
    )
    event: ForeignKey = ForeignKey("tournaments.Events", null=True, blank=True, on_delete=PROTECT)
    name: CharField = CharField(default=f"{strftime('%B')} {strftime('%Y')} Event #{TODAY.month}", max_length=256)
    points_count: BooleanField = BooleanField(default=True)
    team: BooleanField = BooleanField(default=True)
    paper: BooleanField = BooleanField(default=False)
    facebook_url: CharField = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url: CharField = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)
    description: TextField = TextField(default="TBD")
    complete: BooleanField = BooleanField(default=False)

    objects: Manager = Manager()
    results: TournamentManager = TournamentManager()

    def __str__(self) -> str:
        return str(self.name)

    def get_absolute_url(self) -> str:
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs) -> None:
        self.paper = self.lake.paper if self.lake else self.paper
        if not self.rules:
            self.rules, _ = RuleSet.objects.get_or_create(year=TODAY.year)
        if not self.event:
            self.event, _ = Events.objects.get_or_create(
                type="tournament",
                month=TODAY.month,
                year=TODAY.year,
                date=datetime.date(year=TODAY.year, month=TODAY.month, day=get_last_sunday(month=TODAY.month)),
            )
        if not self.payout_multiplier:
            self.payout_multiplier, _ = PayOutMultipliers.objects.get_or_create(year=self.event.year)
        super().save(*args, **kwargs)
