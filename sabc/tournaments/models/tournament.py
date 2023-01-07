# -*- coding: utf-8 -*-
import datetime

from time import strftime
from decimal import Decimal

from django.apps import apps
from django.urls import reverse
from django.db.models import (
    Model,
    Manager,
    PROTECT,
    CharField,
    TextField,
    DateField,
    TimeField,
    ForeignKey,
    BooleanField,
    SmallIntegerField,
)

from .. import get_last_sunday

from . import CURRENT_YEAR

from .rules import RuleSet
from .results import Result, TeamResult
from .payouts import PayOutMultipliers

DEFAULT_END_TIME = datetime.datetime.time(datetime.datetime.strptime("3:00 pm", "%I:%M %p"))
DEFAULT_START_TIME = datetime.datetime.time(datetime.datetime.strptime("6:00 am", "%I:%M %p"))
DEFAULT_FACEBOOK_URL = "https://www.facebook.com/SouthAustinBassClub"
DEFAULT_INSTAGRAM_URL = "https://www.instagram.com/south_austin_bass_club"


class TournamentManager(Manager):
    def set_places(self, tournament):
        def _set_places(query):
            prev = None
            dqs = [q for q in query if q.disqualified]
            zeros = [
                q
                for q in query
                if not q.buy_in and q.total_weight == Decimal("0") and not q.disqualified
            ]
            buy_ins = [q for q in query if q.buy_in and not q.disqualified]
            weighed_fish = [
                q
                for q in query
                if not q.buy_in and q.total_weight > Decimal("0") and not q.disqualified
            ]
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
        if tournament.team:
            _set_places(TeamResult.objects.filter(tournament=tournament).order_by(*order))
        _set_places(Result.objects.filter(tournament=tournament).order_by(*order))

    def set_points(self, tournament):
        Tournament.results.set_places(tournament)
        if not tournament.points:
            return

        # Anglers that weighed in fish
        query = {
            "tournament": tournament,
            "angler__type": "member",
            "total_weight__gt": 0,
            "disqualified": False,
        }
        points = tournament.max_points
        previous = None
        for result in Result.objects.filter(**query).order_by("place_finish"):
            tie = result.place_finish == previous.place_finish if previous else False
            result.points = points if not tie else previous.points
            result.save()
            previous = result
            points -= 1
            # Anglers who were disqualified, but points awarded were allowed
        query = {
            "dq_points": True,
            "tournament": tournament,
            "angler__type": "member",
            "disqualified": True,
        }
        for result in Result.objects.filter(**query):
            result.points = previous.points - 3 if previous else tournament.max_points
            result.save()
        # Anglers that did not weigh in fish or bought in
        query = {
            "tournament": tournament,
            "angler__type": "member",
            "num_fish": 0,
        }
        for result in Result.objects.filter(**query):
            result.points = previous.points - 2 if previous else 0
            if result.buy_in:
                result.points = previous.points - 4 if previous else tournament.max_points - 4
            result.save()

    def get_big_bass_winner(self, tournament):
        return (
            Result.objects.filter(
                tournament=tournament,
                angler__type="member",
                big_bass_weight__gte=Decimal("5"),
            )
            .order_by("-big_bass_weight")
            .first()
        )

    def get_payouts(self, tournament):
        bb_query = {
            "tournament": tournament,
            "angler__type": "member",
            "big_bass_weight__gte": 5.0,
        }
        bb_exists = Result.objects.filter(**bb_query).count() > 0
        num_anglers = Result.objects.filter(tournament=tournament).count()
        pom = tournament.payout_multiplier
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
    name = CharField(default=f"{strftime('%B')} {strftime('%Y')} Tournament", max_length=512)
    date = DateField(default=get_last_sunday)
    year = SmallIntegerField(default=CURRENT_YEAR)
    team = BooleanField(default=True)
    lake = ForeignKey("tournaments.Lake", null=True, blank=True, on_delete=PROTECT)
    ramp = ForeignKey("tournaments.Ramp", null=True, blank=True, on_delete=PROTECT)
    rules = ForeignKey("tournaments.RuleSet", null=True, blank=True, on_delete=PROTECT)
    paper = BooleanField(default=False)
    start = TimeField(default=DEFAULT_START_TIME)
    finish = TimeField(default=DEFAULT_END_TIME)
    points = BooleanField(default=True)
    payout = ForeignKey("tournaments.TournamentPayOut", null=True, blank=True, on_delete=PROTECT)
    complete = BooleanField(default=False)
    max_points = SmallIntegerField(default=100)
    description = TextField(default="TBD")
    facebook_url = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)
    payout_multiplier = ForeignKey(
        "tournaments.PayOutMultipliers", null=True, blank=True, on_delete=PROTECT
    )

    objects = Manager()
    results = TournamentManager()

    def __str__(self):
        return str(self.name)

    def get_absolute_url(self):
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.rules:
            self.rules, _ = RuleSet.objects.get_or_create(year=CURRENT_YEAR)
        if not self.payout_multiplier:
            self.payout_multiplier, _ = PayOutMultipliers.objects.get_or_create(year=self.year)

        if self.lake:
            self.paper = self.lake.paper
        super().save(*args, **kwargs)
