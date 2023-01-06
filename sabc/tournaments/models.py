# -*- coding: utf-8 -*-
import datetime

from time import strftime
from decimal import Decimal

from django.db.models import (
    Model,
    Manager,
    CASCADE,
    PROTECT,
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
    RULE_INFO,
    PAYOUT_INFO,
    PAYMENT_INFO,
    BIG_BASS_INFO,
    WEIGH_IN_INFO,
    get_last_sunday,
    DEFAULT_END_TIME,
    DEFAULT_START_TIME,
    DEFAULT_FACEBOOK_URL,
    DEFAULT_INSTAGRAM_URL,
    DEFAULT_DEAD_FISH_PENALTY,
)

CURRENT_YEAR = datetime.date.today().year


class PayOutMultipliers(Model):
    class Meta:
        verbose_name_plural = "payout multipliers"

    year = SmallIntegerField(default=CURRENT_YEAR)
    club = DecimalField(default=Decimal("3"), max_digits=4, decimal_places=2)
    place_1 = DecimalField(default=Decimal("7"), max_digits=4, decimal_places=2)
    place_2 = DecimalField(default=Decimal("5"), max_digits=4, decimal_places=2)
    place_3 = DecimalField(default=Decimal("4"), max_digits=4, decimal_places=2)
    charity = DecimalField(default=Decimal("2"), max_digits=4, decimal_places=2)
    big_bass = DecimalField(default=Decimal("4"), max_digits=4, decimal_places=2)
    entry_fee = DecimalField(default=Decimal("25"), max_digits=5, decimal_places=2)
    paid_places = SmallIntegerField(default=3)
    per_boat_fee = DecimalField(default=Decimal("50"), max_digits=5, decimal_places=2)
    fee_breakdown = TextField(default="")

    def __str__(self):
        return f"POM: {self.year} Entry Fee: {self.entry_fee}"

    def get_fee_breakdown(self):
        tmnt_pot = sum([self.place_1, self.place_2, self.place_3])
        return "\n".join(
            [
                "Breakdown of the Entry Fee:",
                f"${tmnt_pot:.2f} to the Tournament Pot",
                f"1st ${self.place_1:.2f}, 2nd ${self.place_2:.2f}, 3rd ${self.place_3:.2f}",
                f"${self.big_bass:.2f} to the Tournament Big Bass Pot OVER 5 lbs.",
                f"${self.club:.2f} will go towards Clubs Funds",
                f"${self.charity:.2f} Charity of the clubs choosing",
            ]
        )

    def save(self, *args, **kwargs):
        total = sum(
            [self.club, self.charity, self.place_1, self.place_2, self.place_3, self.big_bass]
        )
        if total != self.entry_fee:
            raise ValueError(
                f"Fee breakdown: {total} does not add up to entry fee: {self.entry_fee}"
            )
        self.per_boat_fee = self.entry_fee * 2
        self.fee_breakdown = self.fee_breakdown or self.get_fee_breakdown()
        super().save(*args, **kwargs)


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
    big_bass_paid = BooleanField(default=False)


class RuleSet(Model):
    year = SmallIntegerField(default=datetime.date.today().year)
    name = CharField(default=f"SABC Default Rules {datetime.date.today().year}", max_length=100)
    rules = TextField(default=RULE_INFO)
    payout = TextField(default=PAYOUT_INFO)
    weigh_in = TextField(default=WEIGH_IN_INFO)
    entry_fee = TextField(default=PAYMENT_INFO)
    limit_num = SmallIntegerField(default=5)
    dead_fish_penalty = DecimalField(
        default=DEFAULT_DEAD_FISH_PENALTY, max_digits=5, decimal_places=2
    )
    big_bass_breakdown = TextField(default=BIG_BASS_INFO)

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
        # Anglers that did not weigh in fish or bought in
        query = {
            "tournament": tournament,
            "angler__type": "member",
            "num_fish": 0,
        }
        buy_in_pts = 0
        for result in Result.objects.filter(**query):
            result.points = previous.points - 2 if previous else 0
            if result.buy_in:
                result.points = previous.points - 4 if previous else tournament.max_points - 4
                buy_in_pts = result.points
            result.save()
        # Anglers who were disqualified, but points awarded were allowed
        query = {
            "dq_points": True,
            "tournament": tournament,
            "angler__type": "member",
            "disqualified": True,
        }
        for result in Result.objects.filter(**query):
            result.points = buy_in_pts + 1
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
    year = SmallIntegerField(default=datetime.date.today().year)
    team = BooleanField(default=True)
    lake = ForeignKey(Lake, null=True, blank=True, on_delete=CASCADE)
    ramp = ForeignKey(Ramp, null=True, blank=True, on_delete=CASCADE)
    rules = ForeignKey(RuleSet, null=True, blank=True, on_delete=CASCADE)
    paper = BooleanField(default=False)
    start = TimeField(default=DEFAULT_START_TIME)
    finish = TimeField(default=DEFAULT_END_TIME)
    points = BooleanField(default=True)
    payout = ForeignKey(TournamentPayOut, null=True, blank=True, on_delete=CASCADE)
    complete = BooleanField(default=False)
    max_points = SmallIntegerField(default=100)
    description = TextField(default="TBD")
    facebook_url = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)
    payout_multiplier = ForeignKey(PayOutMultipliers, null=True, blank=True, on_delete=PROTECT)

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


class Result(Model):
    angler = ForeignKey(Angler, on_delete=CASCADE)
    buy_in = BooleanField(default=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    num_fish = SmallIntegerField(default=0)
    dq_points = BooleanField(default=False)
    tournament = ForeignKey(Tournament, on_delete=CASCADE, null=False, blank=False)
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
    result_1 = ForeignKey(Result, on_delete=CASCADE)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=CASCADE)
    tournament = ForeignKey(Tournament, on_delete=CASCADE)

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
