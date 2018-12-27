# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

# pylint: disable=E1120
from django.db import models

from tournaments import LAKES
from users.models import Angler


class Tournament(models.Model):
    """This model represents a tournament"""
    deleted = models.BooleanField(default=False)

    TYPE_TEAM = 'team'
    TYPE_INDIVIDUAL = 'individual'
    TYPE_CHOICES = (
        (TYPE_TEAM, 'team'),
        (TYPE_INDIVIDUAL, 'individual'),
    )

    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    name = models.CharField(max_length=128)
    date = models.DateField()
    ramp = models.CharField(max_length=128)
    lake = models.CharField(max_length=48, choices=LAKES)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=128)
    paper = models.BooleanField(default=False)
    num_days = models.IntegerField(default=1)

    def __str__(self):
        return '%s %s %s' % (self.name, self.lake, self.ramp)

    class Meta:
        verbose_name_plural = 'Tournaments'
        unique_together = ('date', 'lake', 'city')


class IndividualInfo(models.Model):
    angler = models.ForeignKey(Angler)
    is_boater = models.BooleanField(default=False)

    tournament = models.ForeignKey(Tournament)

    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    penalty_deduction = models.FloatField(default=0.0)


class TeamInfo(models.Model):
    """This model represents the information for an individual tournament"""
    boater = models.ForeignKey(Angler, related_name='boater')
    non_boater = models.ForeignKey(Angler, related_name='non_boater')
