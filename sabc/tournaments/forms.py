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
        exclude = ["created_by", "updated_by"]


class ResultForm(forms.ModelForm):
    """Result form"""

    class Meta:
        """Result metadata"""

        model = Result
        fields = "__all__"


class TeamForm(forms.ModelForm):
    """Team form"""

    class Meta:
        """Team metadata"""

        model = TeamResult
        fields = "__all__"
