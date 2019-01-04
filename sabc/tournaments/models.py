# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from tournaments import LAKES, TOURNAMENT_TYPES, STATES
from users.models import Angler


class Tournament(models.Model):
    """This model represents a tournament"""
    deleted = models.BooleanField(default=False)
    type = models.CharField(max_length=10, choices=TOURNAMENT_TYPES)
    name = models.CharField(max_length=128)
    date = models.DateField()
    ramp = models.CharField(max_length=128)
    lake = models.CharField(max_length=10, choices=LAKES)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=STATES, default='TX')
    paper = models.BooleanField(default=False)
    num_days = models.IntegerField(default=1)

    def __unicode__(self):
        return '%s: LAKE %s-%s' % (self.date, self.lake.__str__().upper(),
                                   self.type.__str__().upper())

    class Meta:
        verbose_name_plural = 'Tournaments'
        unique_together = ('date', 'lake', 'city')


class IndividualResult(models.Model):
    """This model represents an individuals performance in a tournament"""
    deleted = models.BooleanField(default=False)

    tournament = models.ForeignKey(Tournament, null=True, blank=True)

    angler = models.ForeignKey(Angler)
    is_boater = models.BooleanField(default=False)
    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    penalty_deduction = models.FloatField(default=0.0)

    class Meta:
        verbose_name_plural = 'Individual Results'


class TeamResult(models.Model):
    """This model represents the results for an teams performance in a tournament"""
    deleted = models.BooleanField(default=False)

    boater = models.ForeignKey(Angler, related_name='boater')
    non_boater = models.ForeignKey(Angler, related_name='non_boater')
