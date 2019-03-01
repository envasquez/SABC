# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import time

from django.db import models

from tournaments import LAKES, TOURNAMENT_TYPES, STATES, PAPER_LENGTH_TO_WT
from users.models import Profile


class Tournament(models.Model):
    """Tournament model"""
    deleted = models.BooleanField(default=False)

    type = models.CharField(default=TOURNAMENT_TYPES[1][1], max_length=48, choices=TOURNAMENT_TYPES)
    name = models.CharField(
        default='%s %s Tournament - %s' % (
            time.strftime('%B'),  # Month Name
            time.strftime('%Y'),  # Year
            time.strftime('%m')), # Tournament # for the year
            null=True, max_length=128)
    date = models.DateField(null=True)
    lake = models.CharField(blank=True, max_length=100, choices=LAKES)
    ramp = models.CharField(blank=True, max_length=128)

    days = models.IntegerField(default=1)
    start = models.TimeField(blank=True, null=True)
    finish = models.TimeField(blank=True, null=True)
    state = models.CharField(max_length=16, choices=STATES, default='TX')
    points = models.BooleanField(default=True)
    entry_fee = models.IntegerField(default=20)
    description = models.TextField(null=True, blank=True)
    organization = models.CharField(max_length=128, default='SABC', choices=Profile.CLUBS)
    ramp_url = models.CharField(max_length=1024, blank=True)
    facebook_url = models.CharField(max_length=1024, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.fee_per_boat = True if self.type == TOURNAMENT_TYPES[0][0] else False
        super(Tournament, self).save(*args, **kwargs)


class Team(models.Model):
    """This model represents a team in a tournament"""
    angler_1 = models.ForeignKey(Profile)
    angler_2 = models.ForeignKey(Profile, null=True, related_name='+')
    tournament = models.ForeignKey(Tournament)

    def __str__(self):
        t_name = '' if self.tournament is None else self.tournament.name
        return 'Team: %s & %s %s ' % (
            self.angler_1.user.last_name,
            self.angler_2.user.last_name,
            t_name)


class Result(models.Model):
    """This model represents an individuals performance in a tournament"""
    deleted = models.BooleanField(default=False)
    tournament = models.ForeignKey(Tournament, null=True)
    angler = models.ForeignKey(Profile, null=True)
    boater = models.BooleanField(default=False)
    day_num = models.IntegerField(default=1)
    bought_in = models.BooleanField(default=False)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    pentalty_weight = models.FloatField(default=0.0)
    total_weight = models.FloatField(default=0.0)

    def __str__(self):
        t_name = '' if self.tournament is None else self.tournament.name
        return '%s: %s %.2flbs' % (self.angler.user.get_full_name(), t_name, self.total_weight)

    def save(self, *args, **kwargs):
        if self.bought_in is True:
            self.total_weight = 0.0
            self.num_fish_dead = 0.0
            self.num_fish_alive = 0.0
        else:
            self.pentalty_weight = self.num_fish_dead * self.pentalty_weight
            self.total_weight = self.total_weight - self.pentalty_weight
        super(Result, self).save(*args, **kwargs)


class PaperResult(Result):
    """This model represents the results of a paper tournament"""
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