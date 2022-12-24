# -*- coding: utf-8 -*-
import logging
import datetime

from time import strftime
from decimal import Decimal

from django.db.models import (
    Model,
    Manager,
    CASCADE,
    TimeField,
    CharField,
    TextField,
    DateField,
    DO_NOTHING,
    ForeignKey,
    DecimalField,
    BooleanField,
    SmallIntegerField,
)
from django.urls import reverse

# from polls.models import Lakes
from users.models import Angler

from . import (
    LAKES,
    RULE_INFO,
    PAYOUT,
    WEIGH_IN,
    PAYMENT,
    FEE_BREAKDOWN,
    DEFAULT_END_TIME,
    ENTRY_FEE_DOLLARS,
    DEAD_FISH_PENALTY,
    DEFAULT_START_TIME,
    BIG_BASS_BREAKDOWN,
    DEFAULT_PAID_PLACES,
    DEFAULT_FACEBOOK_URL,
    DEFAULT_INSTAGRAM_URL,
    get_last_sunday,
    get_weight_from_length,
)


class RuleSet(Model):
    name = CharField(default="SABC Default Rules", max_length=100)
    fee = DecimalField(default=ENTRY_FEE_DOLLARS, max_digits=5, decimal_places=2)
    rules = TextField(default=RULE_INFO)
    payout = TextField(default=PAYOUT)
    weigh_in = TextField(default=WEIGH_IN)
    entry_fee = TextField(default=PAYMENT)
    fee_breakdown = TextField(default=FEE_BREAKDOWN)
    dead_fish_penalty = DecimalField(default=DEAD_FISH_PENALTY, max_digits=5, decimal_places=2)
    big_bass_breakdown = TextField(default=BIG_BASS_BREAKDOWN)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"RuleSet-{self.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class TournamentManager(Manager):
    def set_places(self, tournament):
        def _set_places(query):
            prev = None
            zeros = [q for q in query if not q.buy_in and q.total_weight == Decimal("0")]
            buy_ins = [q for q in query if q.buy_in]
            weighed_fish = [q for q in query if not q.buy_in and q.total_weight > Decimal("0")]
            for result in weighed_fish[: tournament.paid_places]:
                result.place_finish = 1 if not prev else prev.place_finish + 1
                result.save()
                prev = result
                logging.debug(result)
            # It should be guranteed that there is a prev result at this point
            for result in weighed_fish[tournament.paid_places :]:
                tie = result.total_weight == prev.total_weight
                result.place_finish = prev.place_finish + 1 if not tie else prev.place_finish
                result.save()
                prev = result
                logging.debug(result)
            # Set places & points for anglers who weighed in zero fish
            place = prev.place_finish + 1 if prev else 1
            for result in zeros:
                result.place_finish = place
                result.save()
                logging.debug(result)
                prev = result
            # Set places & points for the anglers that bought-in
            place = place + 1 if len(zeros) != 0 else place
            for result in buy_ins:
                result.place_finish = place
                result.save()
                logging.debug(result)

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

        query = {
            "tournament": tournament,
            "angler__type__in": ["officer", "member"],
            "total_weight__gt": 0,
        }
        points = tournament.max_points
        previous = None
        for result in Result.objects.filter(**query).order_by("place_finish"):
            tie = result.place_finish == previous.place_finish if previous else False
            result.points = points if not tie else previous.points
            result.save()
            previous = result
            points -= 1
            logging.debug(result)

        query = {"tournament": tournament, "angler__type__in": ["officer", "member"], "num_fish": 0}
        for result in Result.objects.filter(**query):
            result.points = previous.points - 2 if previous else 0
            if result.buy_in:
                result.points = previous.points - 4 if previous else tournament.max_points - 4
            result.save()
            logging.debug(result)

    def get_big_bass_winner(self, tournament):
        return (
            Result.objects.filter(
                tournament=tournament,
                angler__type__in=["officer", "member"],
                big_bass_weight__gte=Decimal("5"),
            )
            .order_by("-big_bass_weight")
            .first()
        )

    def get_payouts(self, tournament):
        bb_query = {
            "tournament": tournament,
            "big_bass_weight__gte": 5.0,
            "angler__type__in": ["officer", "member"],
        }
        bb_exists = Result.objects.filter(**bb_query).count() > 0
        num_anglers = Result.objects.filter(tournament=tournament).count()
        return {
            "club": Decimal("3") * num_anglers,
            "total": tournament.fee * num_anglers,
            "place_1": Decimal("6") * num_anglers,
            "place_2": Decimal("4") * num_anglers,
            "place_3": Decimal("3") * num_anglers,
            "charity": Decimal("2") * num_anglers,
            "big_bass": Decimal("2") * num_anglers,
            "bb_carry_over": not bb_exists,
        }


class Tournament(Model):
    fee = DecimalField(default=Decimal("20"), max_digits=5, decimal_places=2)
    name = CharField(default=f"Event #{strftime('%m')} {strftime('%Y')}", max_length=512)
    date = DateField(null=False, blank=False, default=get_last_sunday)
    year = SmallIntegerField(null=False, blank=False, default=datetime.date.today().year)
    team = BooleanField(default=True)
    lake = CharField(default="", blank=False, null=False, max_length=512)
    # lake = ForeignKey(Lakes, blank=False, null=False, on_delete=DO_NOTHING)
    rules = ForeignKey(RuleSet, null=True, blank=True, on_delete=DO_NOTHING)
    paper = BooleanField(default=False)
    start = TimeField(blank=False, null=False, default=DEFAULT_START_TIME)
    finish = TimeField(blank=False, null=False, default=DEFAULT_END_TIME)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
    ramp_url = CharField(default="", max_length=1024, blank=True)
    limit_num = SmallIntegerField(default=5)
    max_points = SmallIntegerField(default=100)
    paid_places = SmallIntegerField(default=DEFAULT_PAID_PLACES)
    description = TextField(default="TBD")
    facebook_url = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)

    objects = Manager()
    results = TournamentManager()

    def __str__(self):
        return str(self.name)

    def get_absolute_url(self):
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        if not self.rules:
            self.rules = RuleSet.objects.create()
        self.ramp_url = self.ramp_url.replace('width="600"', 'width="700"')
        super().save(*args, **kwargs)


class Result(Model):
    angler = ForeignKey(Angler, null=False, blank=False, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False, null=False, blank=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    num_fish = SmallIntegerField(default=0, null=False, blank=False)
    tournament = ForeignKey(Tournament, on_delete=CASCADE, null=False, blank=False)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(
        default=Decimal("0"), null=False, blank=False, max_digits=5, decimal_places=2
    )
    num_fish_dead = SmallIntegerField(default=0, null=False, blank=False)
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
        self.big_bass_weight = self.big_bass_weight
        if self._state.adding:  # Calcualte weights, penalties
            self.penalty_weight = self.num_fish_dead * self.tournament.rules.dead_fish_penalty
            self.total_weight = self.total_weight - self.penalty_weight
            self.num_fish_alive = self.num_fish - self.num_fish_dead

        super().save(*args, **kwargs)


class PaperResult(Result):
    fish1_wt = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish2_wt = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish3_wt = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish4_wt = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish5_wt = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish1_len = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish2_len = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish3_len = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish4_len = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    fish5_len = DecimalField(default=Decimal("0"), decimal_places=2, max_digits=5)
    total_num_fish = SmallIntegerField(default=0, blank=True, null=True)

    def get_absolute_url(self):
        return reverse("result-create", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        self.fish1_wt = Decimal(str(get_weight_from_length(self.fish1_len)))
        self.fish2_wt = Decimal(str(get_weight_from_length(self.fish2_len)))
        self.fish3_wt = Decimal(str(get_weight_from_length(self.fish3_len)))
        self.fish4_wt = Decimal(str(get_weight_from_length(self.fish4_len)))
        self.fish5_wt = Decimal(str(get_weight_from_length(self.fish5_len)))
        self.total_weight = sum(
            [self.fish1_wt, self.fish2_wt, self.fish3_wt, self.fish4_wt, self.fish5_wt]
        )
        big_fish = [
            fish
            for fish in [self.fish1_wt, self.fish2_wt, self.fish3_wt, self.fish4_wt, self.fish5_wt]
            if fish >= Decimal("5")
        ]
        if any(big_fish):
            self.big_bass_weight = max(big_fish)
        super().save(*args, **kwargs)


class TeamResult(Model):
    result_1 = ForeignKey(Result, null=False, blank=False, on_delete=DO_NOTHING)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=DO_NOTHING)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)

    buy_in = BooleanField(default=False, null=True, blank=True)
    num_fish = SmallIntegerField(default=0, null=True, blank=True)
    team_name = CharField(default="", max_length=1024, null=True, blank=True)
    place_finish = SmallIntegerField(default=0, null=True, blank=True)
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
        return reverse("team-details", kwargs={"pk": self.id})

    def get_team_name(self):
        name = ""
        if self.result_1 and not self.result_2:
            return f"{self.result_1.angler.user.get_full_name()} - solo"

        return f"{name} & {self.result_2.angler.user.get_full_name()}"

    def save(self, *args, **kwargs):
        if self._state.adding:
            if self.result_2:
                self.num_fish = sum([self.result_1.num_fish, self.result_2.num_fish])
                self.total_weight = sum([self.result_1.total_weight, self.result_2.total_weight])
                self.num_fish_dead = sum([self.result_1.num_fish, self.result_2.num_fish_dead])
                self.penalty_weight = sum(
                    [self.result_1.penalty_weight, self.result_2.penalty_weight]
                )
                self.num_fish_alive = sum(
                    [self.result_1.num_fish_alive, self.result_2.num_fish_alive]
                )

                self.big_bass_weight = max(
                    [self.result_1.big_bass_weight, self.result_2.big_bass_weight]
                )
            else:
                for attr in [
                    "buy_in",
                    "num_fish",
                    "team_name",
                    "total_weight",
                    "big_bass_weight",
                    "num_fish_alive",
                    "num_fish_dead",
                    "penalty_weight",
                ]:
                    setattr(self, attr, getattr(self.result_1, attr))

        self.team_name = self.get_team_name()

        super().save(*args, **kwargs)
