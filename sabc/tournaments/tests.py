# -*- coding: utf-8 -*-
# pylint: disable=line-too-long
"""Unittests for Tournaments, Results and TeamsResults"""
from django.test import TestCase

from .models import Tournament, TOURNAMENT_TYPES

#
# Tournament model data (for reference)
#


# type = models.CharField(default=TOURNAMENT_TYPES[1][1], max_length=48, choices=TOURNAMENT_TYPES)
# name = models.CharField(default=f"{strftime('%B')} {strftime('%Y')} Tournament - {strftime('%m')}", null=True, max_length=128)
# date = models.DateField(null=True)
# lake = models.CharField(default="TBD", max_length=100, choices=LAKES)
# ramp = models.CharField(default="TBD", max_length=128)
# days = models.IntegerField(default=1)
# rules = models.ForeignKey(RuleSet, null=True, on_delete=models.DO_NOTHING)
# state = models.CharField(max_length=16, choices=STATES, default="TX")
# start = models.TimeField(blank=True, null=True)
# finish = models.TimeField(blank=True, null=True)
# points = models.BooleanField(default=True)
# created_by = models.ForeignKey(Angler, on_delete=models.DO_NOTHING)
# updated_by = models.ForeignKey(Angler, null=True, related_name="+", on_delete=models.DO_NOTHING)
# description = models.TextField(default=f"Tournament #{strftime('%m')} of the {strftime('%Y')} season")
# organization = models.CharField(max_length=128, default="SABC", choices=CLUBS)
# complete = models.BooleanField(default=False)
# ramp_url = models.CharField(default="", max_length=1024, blank=True)
# facebook_url = models.CharField(max_length=1024, blank=True)
# fee = models.DecimalField(max_digits=MAX_PRICE_DIGITS[0], decimal_places=MAX_PRICE_DIGITS[1])


class TestIndividialTournament(TestCase):
    """Unit tests for Tournament Creation"""

    def setUp(self):
        """Default per test setup"""
        self.indiv_t = Tournament.objects.create()

    def test_tournament_type(self):
        """Test Tournament type"""
        self.assertEqual(self.indiv_t.type, TOURNAMENT_TYPES[1][1])
