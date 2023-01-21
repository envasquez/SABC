# -*- coding: utf-8 -*-
from typing import Type

from betterforms.multiform import MultiForm
from django.forms import FileField, Form, ModelForm

from .models.results import Result, TeamResult
from .models.tournament import Events, Tournament


class TournamentForm(ModelForm):
    class Meta:
        model: Type[Tournament] = Tournament
        fields: str = "__all__"
        # exclude: tuple = ("event", "created_by", "updated_by", "payout")


class EventForm(ModelForm):
    class Meta:
        model: Type[Events] = Events
        fields: str = "__all__"


class TournamentEventMultiForm(MultiForm):
    form_classes = {"tournament": TournamentForm, "event": EventForm}


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
    yaml_upload: FileField = FileField()
