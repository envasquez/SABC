# -*- coding: utf-8 -*-
import datetime
from decimal import Decimal
from time import strftime

from django.db.models import (
    PROTECT,
    BooleanField,
    CharField,
    ForeignKey,
    Model,
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
    lake: ForeignKey = ForeignKey("tournaments.Lake", null=True, blank=True, on_delete=PROTECT)
    ramp: ForeignKey = ForeignKey("tournaments.Ramp", null=True, blank=True, on_delete=PROTECT)
    rules: ForeignKey = ForeignKey("tournaments.RuleSet", null=True, blank=True, on_delete=PROTECT)
    payout_multiplier: ForeignKey = ForeignKey(
        "tournaments.PayOutMultipliers", null=True, blank=True, on_delete=PROTECT
    )
    event: ForeignKey = ForeignKey("tournaments.Events", null=True, blank=True, on_delete=PROTECT)
    name: CharField = CharField(
        default=f"{strftime('%B')} {strftime('%Y')} Event #{datetime.date.today().month}", max_length=256
    )
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
                date=datetime.date(year=today.year, month=today.month, day=get_last_sunday(month=today.month)),
            )
        if not self.payout_multiplier:
            self.payout_multiplier, _ = PayOutMultipliers.objects.get_or_create(year=self.event.year)
        super().save(*args, **kwargs)


def get_last_place(tid):
    """Returns the last place result number"""
    results = Result.objects.filter(tournament=tid).order_by("place_finish")
    if results:
        return results.last().place_finish or 1
    return 1


def get_last_points(tid):
    results = Result.objects.filter(tournament=tid).order_by("-points")
    if results:
        return results.last().points
    return Tournament.objects.get(id=tid).rules.max_points


def set_places(tid):
    def _set_places(query):
        prev = None
        dqs = [q for q in query if q.disqualified]
        zeros = [q for q in query if not q.buy_in and q.total_weight == Decimal("0") and not q.disqualified]
        buy_ins = [q for q in query if q.buy_in and not q.disqualified]
        weighed_fish = [q for q in query if not q.buy_in and q.total_weight > Decimal("0") and not q.disqualified]
        # Results for anglers "In the money"
        for result in weighed_fish[: tournament.payout_multiplier.paid_places]:
            result.place_finish = 1 if not prev else prev.place_finish + 1
            result.save()
            prev = result
        # All other anglers who weighed in fish (i.e. did not zero)
        for result in weighed_fish[tournament.payout_multiplier.paid_places :]:
            tie = result.total_weight == prev.total_weight
            result.place_finish = prev.place_finish + 1 if not tie else prev.place_finish
            result.save()
            prev = result
        place = prev.place_finish + 1 if prev else 1
        # All of the anglers who fished, but caught nothing
        for result in zeros:
            result.place_finish = place
            result.save()
            prev = result
        place = place + 1 if zeros else place
        # All of the anglers that "Bought-in"
        for result in buy_ins:
            result.place_finish = place
            result.save()
        # Anglers who were disqualified
        place = place + 1 if buy_ins else place
        for result in dqs:
            result.place_finish = place
            result.save()

    #
    # Set Places
    #
    order = ("-total_weight", "-big_bass_weight", "-num_fish")
    tournament = Tournament.objects.get(id=tid)
    _set_places(Result.objects.filter(tournament=tid).order_by(*order))
    if tournament.team:
        _set_places(TeamResult.objects.filter(tournament=tid).order_by(*order))


def set_points(tid):
    tournament = Tournament.objects.get(id=tid)
    set_places(tid=tid)
    if not tournament.points_count:
        return
    # Anglers that weighed in fish
    points = tournament.rules.max_points
    previous = None
    for result in get_non_zeroes(tid=tid).order_by("place_finish"):
        tie = result.place_finish == previous.place_finish if previous else False
        result.points = points if not tie else previous.points
        result.save()
        previous = result
        points -= 1
    dq_offset = tournament.rules.disqualified_points_offset
    # Anglers who were disqualified, but points awarded were allowed
    for result in get_disqualified(tid=tid):
        result.points = previous.points - dq_offset if previous else tournament.max_points
        result.save()
    # Anglers that did not weigh in fish or bought in
    zeros_offset = tournament.rules.zeroes_points_offset
    buy_in_offset = tournament.rules.buy_ins_points_offset
    for result in get_zeroes(tid=tid):
        result.points = previous.points - zeros_offset if previous else 0
        if result.buy_in:
            result.points = previous.points - buy_in_offset if previous else tournament.max_points - buy_in_offset
        result.save()


def get_non_zeroes(tid):
    query = {"tournament__id": tid, "locked": False, "disqualified": False, "num_fish__gt": 0}
    order = ("-total_weight", "-big_bass_weight", "-num_fish")
    return Result.objects.filter(**query).order_by(*order)


def get_zeroes(tid):
    query = {"buy_in": False, "num_fish": 0, "tournament__id": tid, "disqualified": False, "locked": False}
    return Result.objects.filter(**query)


def get_buy_ins(tid):
    return Result.objects.filter(tournament=tid, buy_in=True)


def get_disqualified(tid):
    order = ("-total_weight", "-big_bass_weight", "-num_fish")
    return Result.objects.filter(tournament=tid, disqualified=True).order_by(*order)


def get_big_bass_winner(tid):
    query = {"angler__member": True, "tournament__id": tid, "big_bass_weight__gte": Decimal("5")}
    bb_results = Result.objects.filter(**query)
    return bb_results.first() if len(bb_results) == 1 else None


def get_payouts(tid):
    bb_query = {"angler__member": True, "tournament__id": tid, "big_bass_weight__gte": Decimal("5")}
    bb_exists = Result.objects.filter(**bb_query).count() > 0
    num_anglers = Result.objects.filter(tournament=tid).count()
    pom = Tournament.objects.get(id=tid).payout_multiplier
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
