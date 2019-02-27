# -*- coding: utf-8 -*-
"""Tournament Models"""
# pylint: disable=import-error
from __future__ import unicode_literals

import time

from django.db import models

from tournaments import LAKES, TOURNAMENT_TYPES, STATES
from users.models import Profile



class Tournament(models.Model):
    """Tournament model"""
    deleted = models.BooleanField(default=False)

    type = models.CharField(default=TOURNAMENT_TYPES[1][0], max_length=48, choices=TOURNAMENT_TYPES)
    name = models.CharField(
        default='%s %s Tournament - %s' % (
            time.strftime('%B'),  # Month Name
            time.strftime('%Y'),  # Year
            time.strftime('%m')), # Month/Tournament # for the year
            null=True, max_length=128)
    date = models.DateField(null=True)
    lake = models.CharField(blank=True, max_length=100, choices=LAKES)
    ramp = models.CharField(blank=True, max_length=128)
    state = models.CharField(max_length=16, choices=STATES, default='TX')
    paper = models.BooleanField(default=False)
    start = models.TimeField(blank=True, null=True)
    finish = models.TimeField(blank=True, null=True)
    ramp_url = models.CharField(max_length=1024, blank=True)
    entry_fee = models.IntegerField(default=20)
    organization = models.CharField(max_length=128, default='SABC', choices=Profile.CLUBS)
    dead_fish_penalty = models.FloatField(default=0.25)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.fee_per_boat = True if self.type == TOURNAMENT_TYPES[0][0] else False
        super(Tournament, self).save(*args, **kwargs)


class Team(models.Model):
    angler_1 = models.ForeignKey(Profile)
    angler_2 = models.ForeignKey(Profile, null=True, blank=True, related_name='+')
    tournament = models.ForeignKey(Tournament)


class Result(models.Model):
    """This model represents an individuals performance in a tournament"""
    team = models.ManyToManyField(Team)
    deleted = models.BooleanField(default=False)
    day_num = models.IntegerField(default=1)
    bought_in = models.BooleanField(default=False)
    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    dead_fish_penalty = models.FloatField(default=0.25)
