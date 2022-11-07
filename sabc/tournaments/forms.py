# -*- coding: utf-8 -*-
"""Tournament related forms"""
from __future__ import unicode_literals

from django import forms

from .models import Tournament, Result, TeamResult


class TournamentForm(forms.ModelForm):
    """Tournament Form"""

    class Meta:
        """Tournament metdata"""

        model = Tournament
        fields = "__all__"
        exclude = ("created_by", "updated_by")


class ResultForm(forms.ModelForm):
    """Result form"""

    class Meta:
        """Result metadata

        Attributes:
            angler (ForeignKey) The Angler object these results are associated with.
            buy_in (BooleanField) True if the angler bougt in, False otherwise.
            points (SmallIntegerField) The number of points awarded from the tournament.
            tournament (ForeignKey) The tournament these results are associated with.
            place_finish (SmallIntegerField) The place number the results finish overall.
            num_fish (SmallIntegerField) The number of fish brought to the scales (weighed).
            total_weight (DecimalField) The total amount of fish weighed (in pounds).
            num_fish_dead (SmallIntegerField) Number of fish weighed that were dead.
            penalty_weight (DecimalField) The total amount of weight in penalty.
            num_fish_alive (SmallIntegerField) Number of fish weighed that were alive.
            big_bass_weight (DecimalField) The weight of the biggest bass weighed.
        """

        model = Result
        fields = "__all__"


class TeamForm(forms.ModelForm):
    """Team form"""

    class Meta:
        """Team metadata"""

        model = TeamResult
        fields = ("tournament", "boater", "result_1", "result_2")
