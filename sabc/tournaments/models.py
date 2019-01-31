# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from tournaments import LAKES, TOURNAMENT_TYPES, STATES
from users.models import Profile


class TournamentResult(models.Model):
    """This model represents an individuals performance in a tournament"""
    deleted = models.BooleanField(default=False)

    angler = models.ForeignKey(Profile, null=True, blank=True)
    day_num = models.IntegerField(default=1)
    bought_in = models.BooleanField(default=False)
    is_boater = models.BooleanField(default=False)
    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)

    class Meta:
        verbose_name_plural = 'Tournament Results'

    def __str__(self):
        return '%s %s - bought-in: %s %.2flbs' % (
            self.angler.user.first_name,
            self.angler.user.last_name,
            self.bought_in,
            self.total_weight
        )

class Tournament(models.Model):
    """One Day Tournamen model"""
    type = models.CharField(max_length=48, choices=TOURNAMENT_TYPES)
    paper = models.BooleanField(default=False)
    results = models.ManyToManyField(TournamentResult)
    time_end = models.DateTimeField(null=True, blank=True)
    time_start = models.DateTimeField(null=True, blank=True)
    organization = models.CharField(max_length=128, default='SABC', choices=Profile.CLUBS)
    

    deleted = models.BooleanField(default=False)

    def __str__(self):
        return '%s: LAKE %s-%s' % (self.name, self.lake.__str__().upper(),
                                   self.type.__str__().upper())

    class Meta:
        verbose_name_plural = 'Tournaments'
        unique_together = ('organization', 'type')


class Event(models.Model):
    """Event model to facilitate multi-day tournaments"""
    name = models.CharField(max_length=128)
    ramp = models.CharField(max_length=128)
    lake = models.CharField(max_length=10, choices=LAKES)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=STATES, default='TX')
    date_end = models.DateField()
    date_start = models.DateField()
    tournaments = models.ManyToManyField(Tournament, null=True, blank=True)
    
    deleted = models.BooleanField(default=False)

    def __str__(self):
        return '%s: LAKE %s-%s' % (self.name, self.lake.__str__().upper(),
                                self.type.__str__().upper())

    class Meta:
        verbose_name_plural = 'Events'
        unique_together = ('name', 'lake', 'city')
