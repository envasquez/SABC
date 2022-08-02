# -*- coding: utf-8 -*-
"""Tournament related models"""
from __future__ import unicode_literals

from time import strftime

from django.db import models
from django.urls import reverse

from users import CLUBS
from users.models import Angler

from . import (
    DEFAULT_TOURNAMENT_FEE,
    PAPER_LENGTH_TO_WT,
    LAKES,
    STATES,
    DEFAULT_RULES,
    DEFAULT_PAYOUT,
    DEFAULT_WEIGH_IN,
    TOURNAMENT_TYPES,
    MAX_PRICE_DIGITS,
    DEFAULT_FEE_BREAKDOWN,
    DEFAULT_BIG_BASS_BREAKDOWN,
)


class RuleSet(models.Model):
    """Rules model for tournaments"""

    name = models.CharField(max_length=100, unique=True)
    rules = models.TextField(default=DEFAULT_RULES)
    payout = models.TextField(default=DEFAULT_PAYOUT)
    weigh_in = models.TextField(default=DEFAULT_WEIGH_IN)
    entry_fee = models.IntegerField(default=20)
    fee_breakdown = models.TextField(default=DEFAULT_FEE_BREAKDOWN)
    big_bass_breakdown = models.TextField(default=DEFAULT_BIG_BASS_BREAKDOWN)
    dead_fish_penalty = models.FloatField(default=0.25)

    def save(self, *args, **kwargs):
        if not self.name:
            self.name = f"RuleSet-{self.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Tournament(models.Model):
    """Tournament model"""

    type = models.CharField(default=TOURNAMENT_TYPES[1][1], max_length=48, choices=TOURNAMENT_TYPES)
    name = models.CharField(
        default=f"{strftime('%B')} {strftime('%Y')} Tournament - {strftime('%m')}",
        null=True,
        max_length=128,
    )
    date = models.DateField(null=True)
    lake = models.CharField(default="TBD", max_length=100, choices=LAKES)
    ramp = models.CharField(default="TBD", max_length=128)
    days = models.IntegerField(default=1)
    rules = models.ForeignKey(RuleSet, null=True, on_delete=models.DO_NOTHING)
    state = models.CharField(max_length=16, choices=STATES, default="TX")
    start = models.TimeField(blank=True, null=True)
    finish = models.TimeField(blank=True, null=True)
    points = models.BooleanField(default=True)
    created_by = models.ForeignKey(Angler, on_delete=models.DO_NOTHING, null=True, blank=True)
    updated_by = models.ForeignKey(Angler, null=True, related_name="+", on_delete=models.DO_NOTHING)
    description = models.TextField(
        default=f"Tournament #{strftime('%m')} of the {strftime('%Y')} season"
    )
    organization = models.CharField(max_length=128, default="SABC", choices=CLUBS)
    complete = models.BooleanField(default=False)
    ramp_url = models.CharField(default="", max_length=1024, blank=True)
    facebook_url = models.CharField(max_length=1024, blank=True)
    fee = models.DecimalField(
        default=DEFAULT_TOURNAMENT_FEE,
        max_digits=MAX_PRICE_DIGITS[0],
        decimal_places=MAX_PRICE_DIGITS[1],
    )

    def __str__(self):
        """Return the name of the tournament"""
        return str(self.name)

    def get_absolute_url(self):
        """Get the absolute url of the tournament details"""
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """Save the tournament"""
        self.ramp_url = self.ramp_url.replace('height="450"', 'height="350"')
        super().save(*args, **kwargs)


class Result(models.Model):
    """This model represents an individuals performance in a tournament"""

    tournament = models.ForeignKey(Tournament, null=True, on_delete=models.DO_NOTHING)
    angler = models.ForeignKey(Angler, null=True, on_delete=models.DO_NOTHING)
    boater = models.BooleanField(default=False)
    day_num = models.IntegerField(default=1)
    bought_in = models.BooleanField(default=False)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    pentalty_weight = models.FloatField(default=0.0)
    total_weight = models.FloatField(default=0.0)

    def __str__(self):
        """String representation of a Result object"""
        t_name = "" if self.tournament is None else self.tournament.name
        return f"{self.angler.user.get_full_name()}: {t_name} {self.total_weight:.2f}lbs"

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-add", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save result"""
        if self.bought_in is True:
            self.total_weight = 0.0
            self.num_fish_dead = 0.0
            self.num_fish_alive = 0.0
        else:
            self.pentalty_weight = self.num_fish_dead * self.rules.dead_fish_penalty
            self.total_weight = self.total_weight - self.pentalty_weight
        super().save(*args, **kwargs)


class PaperResult(Result):
    """This model represents the results of a paper tournament"""

    # pylint: disable=too-many-instance-attributes

    fish_1_length = models.FloatField(default=0.0)
    fish_2_length = models.FloatField(default=0.0)
    fish_3_length = models.FloatField(default=0.0)
    fish_4_length = models.FloatField(default=0.0)
    fish_5_length = models.FloatField(default=0.0)
    fish_1_weight = models.FloatField(default=0.0)
    fish_2_weight = models.FloatField(default=0.0)
    fish_3_weight = models.FloatField(default=0.0)
    fish_4_weight = models.FloatField(default=0.0)
    fish_5_weight = models.FloatField(default=0.0)

    def save(self, *args, **kwargs):
        self.total_weight = 0.0
        self.fish_1_weight = PAPER_LENGTH_TO_WT.get(self.fish_1_length, 0.0)
        self.fish_2_weight = PAPER_LENGTH_TO_WT.get(self.fish_2_length, 0.0)
        self.fish_3_weight = PAPER_LENGTH_TO_WT.get(self.fish_3_length, 0.0)
        self.fish_4_weight = PAPER_LENGTH_TO_WT.get(self.fish_4_length, 0.0)
        self.fish_5_weight = PAPER_LENGTH_TO_WT.get(self.fish_5_length, 0.0)
        if self.bought_in is False:
            self.total_weight += self.fish_1_weight
            self.total_weight += self.fish_2_weight
            self.total_weight += self.fish_3_weight
            self.total_weight += self.fish_4_weight
            self.total_weight += self.fish_5_weight
        else:
            self.total_weight = 0.0
            self.fish_1_length = 0.0
            self.fish_2_length = 0.0
            self.fish_3_length = 0.0
            self.fish_4_length = 0.0
            self.fish_5_length = 0.0
            self.num_fish_dead = 0.0
            self.num_fish_alive = 0.0
        super(Result, self).save(*args, **kwargs)


class Team(models.Model):
    """This model represents a team in a tournament"""

    angler_1 = models.ForeignKey(Angler, on_delete=models.DO_NOTHING)
    angler_2 = models.ForeignKey(
        Angler, null=True, blank=True, related_name="+", on_delete=models.DO_NOTHING
    )
    tournament = models.ForeignKey(Tournament, on_delete=models.DO_NOTHING)

    def __str__(self):
        return (
            f"Team: {self.angler_1.user.get_full_name()} & {self.angler_2.user.get_full_name()}"
            if self.angler_2 is not None
            else f"Team: {self.angler_1.user.get_full_name()} - SOLO"
        )

    # def get_absolute_url(self):
    #     return reverse('team-details', kwargs={'pk': self.id})
