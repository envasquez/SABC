# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from tournaments import LAKES, TOURNAMENT_TYPES, STATES
from users.models import Profile


class Tournament(models.Model):
    """Tournamen model"""
    name = models.CharField(max_length=128)
    date = models.DateField()
    type = models.CharField(max_length=48, choices=TOURNAMENT_TYPES)
    ramp = models.CharField(max_length=128)
    lake = models.CharField(max_length=10, choices=LAKES)
    city = models.CharField(max_length=64)
    state = models.CharField(max_length=16, choices=STATES, default='TX')
    paper = models.BooleanField(default=False)
    num_days = models.IntegerField(default=1)
    deleted = models.BooleanField(default=False)
    organization = models.CharField(max_length=128, default='SABC', choices=Profile.CLUBS)

    def __str__(self):
        return '%s: LAKE %s-%s' % (self.date, self.lake.__str__().upper(),
                                   self.type.__str__().upper())

    def __unicode__(self):
        return '%s: LAKE %s-%s' % (self.date, self.lake.__str__().upper(),
                                   self.type.__str__().upper())

    participants = models.ManyToManyField(Profile)

    class Meta:
        verbose_name_plural = 'Tournaments'
        unique_together = ('date', 'lake', 'city')