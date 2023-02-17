# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal

from django.db.models import (
    CASCADE,
    PROTECT,
    BooleanField,
    CharField,
    ForeignKey,
    Model,
    QuerySet,
    TextField,
)
from django.urls import reverse

from .. import get_last_sunday
from .events import Events
from .payouts import PayOutMultipliers
from .results import Result, TeamResult
from .rules import RuleSet

DEFAULT_FACEBOOK_URL: str = "https://www.facebook.com/SouthAustinBassClub"
DEFAULT_INSTAGRAM_URL: str = "https://www.instagram.com/south_austin_bass_club"


class Tournament(Model):
    lake: ForeignKey = ForeignKey(
        "tournaments.Lake", null=True, blank=True, on_delete=CASCADE
    )
    ramp: ForeignKey = ForeignKey(
        "tournaments.Ramp", null=True, blank=True, on_delete=CASCADE
    )
    rules: ForeignKey = ForeignKey(
        "tournaments.RuleSet", null=True, blank=True, on_delete=CASCADE
    )
    payout_multiplier: ForeignKey = ForeignKey(
        "tournaments.PayOutMultipliers", null=True, blank=True, on_delete=PROTECT
    )
    event: ForeignKey = ForeignKey(
        "tournaments.Events", null=True, blank=True, on_delete=PROTECT
    )
    name: CharField = CharField(default="", max_length=256)
    points_count: BooleanField = BooleanField(default=True)
    team: BooleanField = BooleanField(default=True)
    paper: BooleanField = BooleanField(default=False)
    facebook_url: CharField = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url: CharField = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)
    description: TextField = TextField(default="TBD")
    complete: BooleanField = BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.name)

    def get_absolute_url(self) -> str:
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs) -> None:
        today = datetime.date.today()
        if not self.rules:
            self.rules, _ = RuleSet.objects.get_or_create(year=today.year)
        if not self.event:
            self.event, _ = Events.objects.get_or_create(
                type="tournament",
                month=today.month,
                year=today.year,
                date=datetime.date(
                    year=today.year,
                    month=today.month,
                    day=get_last_sunday(month=today.month),
                ),
            )
        if not self.payout_multiplier:
            self.payout_multiplier, _ = PayOutMultipliers.objects.get_or_create(
                year=self.event.year
            )
        if self.lake:
            self.paper = self.lake.paper  # pylint: disable=no-member
        super().save(*args, **kwargs)


def tie(current: Result, previous: Result | None) -> bool:
    return (
        all(
            [
                current.total_weight == previous.total_weight,
                current.num_fish == previous.num_fish,
                current.big_bass_weight == previous.big_bass_weight,
            ]
        )
        if previous
        else False
    )


def set_places(tid: int) -> None:
    def _set_places(query: QuerySet):
        if not query:
            return
        prev: None | Result = None
        place: int = 1
        fished: list[Result] = [q for q in query if not q.disqualified and not q.buy_in]
        for result in fished:
            if tie(current=result, previous=prev):
                result.place_finish = prev.place_finish if prev else place
            else:
                result.place_finish = place
                place += 1
            if isinstance(result, Result):
                if not result.locked:
                    result.save()
            else:
                result.save()
            prev = result
        buy_ins: list = [q for q in query if q.buy_in]
        if buy_ins:
            for buy_in in buy_ins:
                buy_in.place_finish = place
                buy_in.save()
            place += 1
        disqualified: list = [q for q in query if q.disqualified]
        if disqualified:
            for dqs in disqualified:
                dqs.place_finish = place
                dqs.save()

    order: tuple = ("-total_weight", "-big_bass_weight", "-num_fish")
    _set_places(Result.objects.filter(tournament=tid).order_by(*order))
    _set_places(TeamResult.objects.filter(tournament=tid).order_by(*order))


def set_points(tid: int) -> None:
    tournament: Tournament = Tournament.objects.get(id=tid)
    set_places(tid=tid)
    if not tournament.points_count:
        return

    # Anglers that weighed in fish
    points: int = tournament.rules.max_points
    previous: Result | None = None
    for result in get_non_zeroes(tid=tid).order_by("place_finish"):
        if tie(current=result, previous=previous):
            result.points = previous.points if previous else points
        else:
            result.points = points
            points -= 1
        result.save()
        previous = result

    # Anglers who were disqualified, but points awarded were allowed
    dq_offset: int = tournament.rules.disqualified_points_offset
    for result in get_disqualified(tid=tid):
        result.points = (
            previous.points - dq_offset if previous else tournament.rules.max_points
        )
        result.save()

    # Anglers that did not weigh in fish or bought in
    zeros_offset: int = tournament.rules.zeroes_points_offset
    buy_in_offset: int = tournament.rules.buy_ins_points_offset
    for result in get_zeroes(tid=tid):
        result.points = previous.points - zeros_offset if previous else 0
        if result.buy_in:
            result.points = (
                previous.points - buy_in_offset
                if previous
                else tournament.rules.max_points - buy_in_offset
            )
        result.save()


def get_non_zeroes(tid: int) -> QuerySet:
    query: dict = {
        "tournament__id": tid,
        "locked": False,
        "disqualified": False,
        "num_fish__gt": 0,
        "angler__member": True,
    }
    order: tuple = ("-total_weight", "-big_bass_weight", "-num_fish")
    return Result.objects.filter(**query).order_by(*order)


def get_zeroes(tid: int) -> QuerySet[Result]:
    query: dict = {
        "num_fish": 0,
        "tournament__id": tid,
        "disqualified": False,
        "locked": False,
        "angler__member": True,
    }
    return Result.objects.filter(**query)


def get_buy_ins(tid: int) -> QuerySet[Result]:
    return Result.objects.filter(tournament=tid, buy_in=True, angler__member=True)


def get_disqualified(tid: int) -> QuerySet[Result]:
    order = ("-total_weight", "-big_bass_weight", "-num_fish")
    return Result.objects.filter(
        tournament=tid, disqualified=True, angler__member=True
    ).order_by(*order)


def get_big_bass_winner(tid: int) -> Result | None:
    query: dict = {
        "angler__member": True,
        "tournament__id": tid,
        "big_bass_weight__gte": Decimal("5"),
    }
    bb_results = Result.objects.filter(**query)
    return bb_results.first() if bb_results.exists() else None


def get_payouts(tid: int) -> dict:
    bb_query: dict = {
        "angler__member": True,
        "tournament__id": tid,
        "big_bass_weight__gte": Decimal("5"),
    }
    bb_exists: bool = Result.objects.filter(**bb_query).count() > 0
    num_anglers: int = Result.objects.filter(tournament=tid).count()
    pom: PayOutMultipliers = Tournament.objects.get(id=tid).payout_multiplier
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
