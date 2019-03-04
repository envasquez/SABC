# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django import forms

from .models import Tournament, Result, Team

class TournamentForm(forms.ModelForm):

    class Meta:
        model = Tournament
        fields = '__all__'
        exclude = ['created_by', 'updated_by']


class ResultForm(forms.ModelForm):

    class Meta:
        model = Result
        fields = '__all__'


class TeamForm(forms.ModelForm):

    class Meta:
        model = Team
        fields = '__all__'