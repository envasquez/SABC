# -*- coding: utf-8 -*-

from django.forms import FileField, Form, ModelForm

from .models.results import Result, TeamResult
from .models.tournaments import Events, Tournament


class TournamentForm(ModelForm):
    class Meta:
        model = Tournament
        fields = "__all__"
        exclude = ("created_by", "updated_by", "paper")


class EventForm(ModelForm):
    class Meta:
        model = Events
        fields = "__all__"
        exclude = ("type", "month")


class ResultForm(ModelForm):
    class Meta:
        model = Result
        fields = (
            "tournament",
            "angler",
            "buy_in",
            "locked",
            "dq_points",
            "disqualified",
            "num_fish",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )

    def __init__(self, *args, **kwargs):
        angler = kwargs.pop("angler")

        super().__init__(*args, **kwargs)
        self.fields["angler"].queryset = angler


class ResultUpdateForm(ModelForm):
    class Meta:
        model = Result
        fields = (
            "tournament",
            "angler",
            "buy_in",
            "locked",
            "dq_points",
            "disqualified",
            "place_finish",
            "points",
            "num_fish",
            "total_weight",
            "num_fish_dead",
            "big_bass_weight",
        )


class TeamForm(ModelForm):
    class Meta:
        model = TeamResult
        fields = ("tournament", "result_1", "result_2")

    def __init__(self, *args, **kwargs):
        result_1 = kwargs.pop("result_1")
        result_2 = kwargs.pop("result_2")

        super().__init__(*args, **kwargs)
        self.fields["result_1"].queryset = result_1
        self.fields["result_2"].queryset = result_2


class YamlImportForm(Form):
    yaml_upload = FileField()
