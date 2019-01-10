# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models

from users.models import Profile
from tournaments.models import Tournament


class TournamentResult(models.Model):
    """This model represents an individuals performance in a tournament"""
    deleted = models.BooleanField(default=False)

    angler = models.ForeignKey(Profile, null=True, blank=True)
    tournament = models.ForeignKey(Tournament, null=True, blank=True, on_delete=models.CASCADE)

    day_num = models.IntegerField(default=1)
    bought_in = models.BooleanField(default=False)
    is_boater = models.BooleanField(default=False)
    total_weight = models.FloatField(default=0.0)
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    big_bass_weight = models.FloatField(default=0.0)
    penalty_deduction = models.FloatField(default=0.0)

    class Meta:
        verbose_name_plural = 'Tournament Results'

    def __str__(self):
        return '%s %s - bought-in: %s %.2flbs' % (
            self.angler.user.first_name,
            self.angler.user.last_name,
            self.bought_in,
            self.total_weight
        )