# pylint: disable=E1120
from django.db import models

from anglers.models import Angler

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
    lake = models.CharField(max_length=128)
    city = models.CharField(max_length=128)
    state = models.CharField(max_length=128)
    paper = models.BooleanField(default=False)
    num_days = models.IntegerField(default=1)

    class Meta:
        verbose_name_plural = 'Tournaments'
        unique_together = ('date', 'lake', 'city')


class IndividualInfo(models.Model):
    angler = models.ForeignKey(Angler, on_delete=models.PROTECT)
    is_boater = models.BooleanField(default=False)
    
    num_fish_dead = models.IntegerField(default=0)
    num_fish_alive = models.IntegerField(default=0)
    
    total_weight = models.FloatField(default=0.0)
    big_bass_weight = models.FloatField(default=0.0)
    penalty_deduction = models.FloatField(default=0.0)


class TeamInfo(models.Model):
    """This model represents the information for an individual tournament"""
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT)
    boater = models.ForeignKey(Angler, on_delete=models.PROTECT, related_name='boater')
    non_boater = models.ForeignKey(Angler, on_delete=models.PROTECT, related_name='non_boater')
    
