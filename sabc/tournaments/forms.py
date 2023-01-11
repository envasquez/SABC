# -*- coding: utf-8 -*-
from typing import Type

from django.forms import Form, ModelForm, FileField

from .models.results import Result, TeamResult
from .models.tournament import Tournament


class TournamentForm(ModelForm):
    class Meta:
        model: Type[Tournament] = Tournament
        fields: str = "__all__"
        exclude: tuple = ("created_by", "updated_by", "payout")


class ResultForm(ModelForm):
    class Meta:
        model: Type[Result] = Result
        fields: tuple = (
            "tournament",
            "angler",
            "buy_in",
            "num_fish",
            "dq_points",
            "disqualified",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )


class TeamForm(ModelForm):
    class Meta:
        model: Type[TeamResult] = TeamResult
        fields: tuple = ("tournament", "result_1", "result_2")


class YamlImportForm(Form):
    yaml_upload: Type[FileField] = FileField()
