# -*- coding: utf-8 -*-
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
    ForeignKey,
    DecimalField,
    BooleanField,
    SmallIntegerField,
)
from django.urls import reverse

from users.models import Angler

from . import (
    PAYOUT,
    PAYMENT,
    WEIGH_IN,
    RULE_INFO,
    FEE_BREAKDOWN,
    get_last_sunday,
    DEFAULT_END_TIME,
    ENTRY_FEE_DOLLARS,
    DEAD_FISH_PENALTY,
    DEFAULT_START_TIME,
    BIG_BASS_BREAKDOWN,
    DEFAULT_PAID_PLACES,
    DEFAULT_FACEBOOK_URL,
    DEFAULT_INSTAGRAM_URL,
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


class Lake(Model):
    name = CharField(default="TBD", max_length=256)
    paper = BooleanField(default=False)
    google_maps = CharField(default="", max_length=4096)

    class Meta:
        ordering = ("name",)
        verbose_name_plural = "Lakes"

    def __str__(self):  # A little bit of custom code for a few of our local lakes :-)
        if self.name in ["fayette county reservoir", "choke canyon reservoir"]:
            return self.name.title()
        return (
            f"lake {self.name}".title()
            if self.name not in ["inks", "stillhouse hollow", "lady bird", "canyon"]
            else f"{self.name} lake".title()
        )

    def save(self, *args, **kwargs):
        self.name = self.name.lower().replace("lake", "")
        return super().save(*args, **kwargs)


class Ramp(Model):
    lake = ForeignKey(Lake, on_delete=CASCADE)
    name = CharField(max_length=128)
    google_maps = CharField(default="", max_length=4096)

    class Meta:
        ordering = ("lake__name",)
        verbose_name_plural = "Ramps"

    def __str__(self):
        return f"{self.lake}: {self.name.title()}"


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
            for result in weighed_fish[tournament.paid_places :]:
                tie = result.total_weight == prev.total_weight
                result.place_finish = prev.place_finish + 1 if not tie else prev.place_finish
                result.save()
                prev = result
            place = prev.place_finish + 1 if prev else 1
            for result in zeros:
                result.place_finish = place
                result.save()
                prev = result
            place = place + 1 if len(zeros) != 0 else place
            for result in buy_ins:
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

        query = {"tournament": tournament, "angler__type__in": ["officer", "member"], "num_fish": 0}
        for result in Result.objects.filter(**query):
            result.points = previous.points - 2 if previous else 0
            if result.buy_in:
                result.points = previous.points - 4 if previous else tournament.max_points - 4
            result.save()

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
            "place_1": Decimal("7") * num_anglers,
            "place_2": Decimal("5") * num_anglers,
            "place_3": Decimal("4") * num_anglers,
            "charity": Decimal("2") * num_anglers,
            "big_bass": Decimal("4") * num_anglers,
            "bb_carry_over": not bb_exists,
        }


class Tournament(Model):
    fee = DecimalField(default=ENTRY_FEE_DOLLARS, max_digits=5, decimal_places=2)
    name = CharField(default=f"{strftime('%B')} {strftime('%Y')} Tournament", max_length=512)
    date = DateField(default=get_last_sunday)
    year = SmallIntegerField(default=datetime.date.today().year)
    team = BooleanField(default=True)
    lake = ForeignKey(Lake, null=True, blank=True, on_delete=CASCADE)
    ramp = ForeignKey(Ramp, null=True, blank=True, on_delete=CASCADE)
    rules = ForeignKey(RuleSet, null=True, blank=True, on_delete=CASCADE)
    paper = BooleanField(default=False)
    start = TimeField(default=DEFAULT_START_TIME)
    finish = TimeField(default=DEFAULT_END_TIME)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
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
        if self.lake:
            self.paper = self.lake.paper
        super().save(*args, **kwargs)


class PayOutMultipliers(Model):
    class Meta:
        verbose_name_plural = "payout multipliers"

    year = SmallIntegerField(default=datetime.date.today().year)
    club = SmallIntegerField(default=3)
    place_1 = SmallIntegerField(default=7)
    place_2 = SmallIntegerField(default=5)
    place_3 = SmallIntegerField(default=4)
    charity = SmallIntegerField(default=2)
    big_bass = SmallIntegerField(default=4)
    entry_fee = DecimalField(default=ENTRY_FEE_DOLLARS, max_digits=5, decimal_places=2)
    tournament = ForeignKey(Tournament, on_delete=CASCADE)


class TournamentPayOut(Model):
    class Meta:
        verbose_name_plural = "tournament payouts"

    club = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    offset = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_1 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_2 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    place_3 = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    charity = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    big_bass = DecimalField(default=Decimal("0"), max_digits=6, decimal_places=2)
    tournament = ForeignKey(Tournament, on_delete=CASCADE)
    big_bass_paid = BooleanField(default=False)


class Result(Model):
    angler = ForeignKey(Angler, on_delete=CASCADE)
    buy_in = BooleanField(default=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    num_fish = SmallIntegerField(default=0)
    tournament = ForeignKey(Tournament, on_delete=CASCADE, null=False, blank=False)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0"), max_digits=5, decimal_places=2)
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
        self.total_weight = self.total_weight - self.penalty_weight
        self.num_fish_alive = self.num_fish - self.num_fish_dead
        super().save(*args, **kwargs)


class TeamResult(Model):
    result_1 = ForeignKey(Result, on_delete=CASCADE)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=CASCADE)
    tournament = ForeignKey(Tournament, on_delete=CASCADE)

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
        self.team_name = self.get_team_name()
        super().save(*args, **kwargs)
