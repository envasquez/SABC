# -*- coding: utf-8 -*-
from django.forms import FileField, Form, ModelForm

from .models.results import Result, TeamResult
from .models.tournament import Events, Tournament


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = "__all__"
        exclude = ("created_by", "updated_by")


class EventForm(ModelForm):
    class Meta:
        model = Events
        fields = "__all__"
        exclude = ("type", "year", "month")


class ResultForm(ModelForm):
    class Meta:
        model = Result
        fields = (
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
        model = TeamResult
        fields = ("tournament", "result_1", "result_2")


class YamlImportForm(Form):
    yaml_upload = FileField()
