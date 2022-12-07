# -*- coding: utf-8 -*-
"""Tournament related forms"""
from __future__ import unicode_literals

from django.forms import ModelForm

from .models import Tournament, Result, TeamResult


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = "__all__"
        exclude = ("created_by", "updated_by", "year")


class ResultForm(ModelForm):
    class Meta:
        model = Result
        fields = (
            "tournament",
            "angler",
            "buy_in",
            "num_fish",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )


class TeamForm(ModelForm):
    class Meta:
        model = TeamResult
        fields = ("tournament", "result_1", "result_2")
