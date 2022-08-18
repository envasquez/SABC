# -*- coding: utf-8 -*-
"""Tournament related models"""
from __future__ import unicode_literals

from django.db.models import (
    Model,
    ForeignKey,
    TimeField,
    CharField,
    TextField,
    IntegerField,
    DecimalField,
    BooleanField,
    FloatField,
    DateField,
    DO_NOTHING,
)
from django.urls import reverse

from users.models import Angler

from . import (
    DEFAULT_DEAD_FISH_PENALTY,
    LAKES,
    DEFAULT_RULES,
    DEFAULT_PAYOUT,
    DEFAULT_WEIGH_IN,
    DEFAULT_FEE_BREAKDOWN,
    DEFAULT_BIG_BASS_BREAKDOWN,
    get_tournament_name,
    get_tournament_description,
    get_length_from_weight,
    get_weight_from_length,
)


class RuleSet(Model):
    """Rules model for tournaments"""

    name = CharField(max_length=100, unique=True)
    rules = TextField(default=DEFAULT_RULES)
    payout = TextField(default=DEFAULT_PAYOUT)
    weigh_in = TextField(default=DEFAULT_WEIGH_IN)
    entry_fee = IntegerField(default=20)
    fee_breakdown = TextField(default=DEFAULT_FEE_BREAKDOWN)
    big_bass_breakdown = TextField(default=DEFAULT_BIG_BASS_BREAKDOWN)
    dead_fish_penalty = FloatField(default=0.25)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"RuleSet-{self.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tournament(Model):
    """Tournament model

    name: Name of the tournqment.
    fee: Entry fee amount
    date: Start date of the tournament.
    team: True if the tournament is a team tournament False otherwise.
    lake: Lake on which the event will take place.
    rules: Rules to be used for this event.
    start: Tournament start time.
    finish: Tournament end time
    points: True if the tournament counts towards AoY points.
    complete: True if the tournament is over, False otherwise.the tournament will last (default=1)
    ramp_url: Google maps embedable link for weigh-in location.
    num_days: Number of days
    limit_num: The number of weighed fish that comprise a limit
    multi_day: True if num_days > 1 False otherwise.
    description: A description of the tournament details.
    facebook_url: URL to the Facebok even or page.
    instagram_url: URL to the Instagram event or page.
    """

    name = CharField(default=get_tournament_name(), max_length=512)
    fee = DecimalField(default=20, max_digits=7, decimal_places=2)
    date = DateField(null=True)
    team = BooleanField(default=True)
    lake = CharField(default="TBD", max_length=100, choices=LAKES)
    rules = ForeignKey(RuleSet, null=True, on_delete=DO_NOTHING)
    start = TimeField(blank=True, null=True)
    finish = TimeField(blank=True, null=True)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
    ramp_url = CharField(default="", max_length=1024, blank=True)
    num_days = IntegerField(default=1)
    limit_num = IntegerField(default=5)
    multi_day = BooleanField(default=False)
    description = TextField(default=get_tournament_description())
    facebook_url = CharField(max_length=1024, blank=True)
    instagram_url = CharField(max_length=1024, blank=True)

    def __str__(self):
        """Return the name of the tournament"""
        return str(self.name)

    def get_absolute_url(self):
        """Get the absolute url of the tournament details"""
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """Save the tournament"""
        self.ramp_url = self.ramp_url.replace('height="450"', 'height="350"')
        if not self.rules:
            self.rules = RuleSet.objects.create()

        super().save(*args, **kwargs)


# pylint: disable=too-many-instance-attributes
class Result(Model):
    """This model represents an individuals performance in a tournament

    angler: The angler these results are associated with
    buy_in: True is the angler bougt in, False otherwise
    day_num: Day number results for the tournament (default=1)
    tournament: The tournament these results are associated with
    total_weight: The total amount of fish weighed
    num_fish_dead: Number of fish weighed that were dead
    num_fish_alive: Number of fish weighed that were alive
    big_bass_weight: The weight of the biggest bass weighed
    pentalty_weight: The total amount of weight in penalty
    num_fish_weighed: Number of fish weighed
    fish_1_wt: The weight of fish number 1
    fish_1_len: The length of fish number 1
    fish_2_wt: The weight of fish number 2
    fish_2_len: The length of fish number 2
    fish_3_wt: The weight of fish number 3
    fish_3_len: The length of fish number 3
    fish_4_wt: The weight of fish number 4
    fish_4_len: The length of fish number 4
    fish_5_wt: The weight of fish number 5
    fish_5_len: The length of fish number 5
    """

    angler = ForeignKey(Angler, null=True, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False)
    day_num = IntegerField(default=1)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)
    total_weight = FloatField(default=0.0)
    num_fish_dead = IntegerField(default=0)
    num_fish_alive = IntegerField(default=0)
    big_bass_weight = FloatField(default=0.0)
    pentalty_weight = FloatField(default=0.0)
    num_fish_weighed = IntegerField(default=0)
    fish_1_wt = FloatField(default=0.0)
    fish_1_len = FloatField(default=0.0)
    fish_1_alive = BooleanField(default=False)
    fish_2_wt = FloatField(default=0.0)
    fish_2_len = FloatField(default=0.0)
    fish_2_alive = BooleanField(default=False)
    fish_3_wt = FloatField(default=0.0)
    fish_3_len = FloatField(default=0.0)
    fish_3_alive = BooleanField(default=False)
    fish_4_wt = FloatField(default=0.0)
    fish_4_len = FloatField(default=0.0)
    fish_4_alive = BooleanField(default=False)
    fish_5_wt = FloatField(default=0.0)
    fish_5_len = FloatField(default=0.0)
    fish_5_alive = BooleanField(default=False)

    def __str__(self):
        """String representation of a Result object"""
        t_name = "" if self.tournament is None else self.tournament.name
        return f"{self.angler.user.get_full_name()}: {t_name} {self.total_weight:.2f}lbs"

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-add", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save the result

        Upon save() ... we should do a few things:
        1. Calculate the total weight (applying the appropriate penalty)
        2. Calculate the number of fish alive (if not entered)
        3. Generate the fish weight based on the length if the length is entered
        4. Generate the fish length based on the weight if the weight is entered
        """
        self.pentalty_weight = self.num_fish_dead * DEFAULT_DEAD_FISH_PENALTY
        # 2. Calculate the number of fish alive
        self.num_fish_alive = self.num_fish_weighed - self.num_fish_dead
        weighed_fish = [
            self.fish_1_wt,
            self.fish_2_wt,
            self.fish_3_wt,
            self.fish_4_wt,
            self.fish_5_wt,
        ]
        measured_fish = [
            self.fish_1_len,
            self.fish_2_len,
            self.fish_3_len,
            self.fish_4_len,
            self.fish_5_len,
        ]
        # 4. Generate the fish length based on the weight if the weight is entered
        if sum(weighed_fish) > 0.0 and sum(measured_fish) == 0.0:  # Weights, not lengths entered
            self.fish_1_len = get_length_from_weight(self.fish_1_wt)
            self.fish_2_len = get_length_from_weight(self.fish_2_wt)
            self.fish_3_len = get_length_from_weight(self.fish_3_wt)
            self.fish_4_len = get_length_from_weight(self.fish_4_wt)
            self.fish_5_len = get_length_from_weight(self.fish_5_wt)
        # 3. Generate the fish weight based on the length if the length is entered
        elif sum(weighed_fish) == 0.0 and sum(measured_fish) > 0.0:  # Lengths, not weights entered
            self.fish_1_wt = get_weight_from_length(self.fish_1_len)
            self.fish_2_wt = get_weight_from_length(self.fish_2_len)
            self.fish_3_wt = get_weight_from_length(self.fish_3_len)
            self.fish_4_wt = get_weight_from_length(self.fish_4_len)
            self.fish_5_wt = get_weight_from_length(self.fish_5_len)
        # 1. Calcualte total weight
        for idx in range(self.tournament.limit_num):
            self.total_weight += weighed_fish[idx]

        self.total_weight = round(self.total_weight - self.pentalty_weight, 2)  # 2 decimal places
        self.big_bass_weight = max(weighed_fish)

        super().save(*args, **kwargs)


class TeamResult(Model):
    """This model represents a team result in a tournament"""

    boater = ForeignKey(Angler, related_name="+", on_delete=DO_NOTHING)
    result_1 = ForeignKey(Result, on_delete=DO_NOTHING)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=DO_NOTHING)

    def __str__(self):
        angler_1 = self.result_1.angler.user.get_full_name()
        if self.result_2:
            angler_2 = self.result_2.angler.user.get_full_name()
            return f"Team: {angler_1} & {angler_2}"

        return f"Team: {angler_1} - SOLO"

    def get_absolute_url(self):
        """Returns the absolute url for this model"""
        return reverse("team-details", kwargs={"pk": self.id})
