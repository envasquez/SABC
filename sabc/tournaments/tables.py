# -*- coding: utf-8 -*-
from django_tables2.utils import A
from django_tables2.tables import Table
from django_tables2.columns import Column, LinkColumn

from .models.results import Result, TeamResult

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


class EditableResultTable(Table):
    delete = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class ResultTable(Table):
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class EditableTeamResultTable(Table):
    delete = LinkColumn(
        "teamresult-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )

    class Meta:
        model = TeamResult
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "team_name",
            "num_fish",
            "big_bass_weight",
            "total_weight",
        )


class TeamResultTable(Table):
    class Meta:
        model = TeamResult
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "team_name",
            "num_fish",
            "big_bass_weight",
            "total_weight",
        )


class EditableBuyInTable(Table):
    delete = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "points",
        )


class BuyInTable(Table):
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "points",
        )


class EditableDQTable(Table):
    delete = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class DQTable(Table):
    first_name = Column(accessor="angler.user.first_name")
    last_name = Column(accessor="angler.user.last_name")

    class Meta:
        model = Result
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
        fields = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class TournamentSummaryTable(Table):
    total_fish = Column()
    total_weight = Column()
    limits = Column()
    zeros = Column()
    buy_ins = Column()
    big_bass = Column()
    heavy_stringer = Column()

    class Meta:
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE


class PayoutSummary(Table):
    first = Column(accessor="place_1")
    second = Column(accessor="place_2")
    third = Column(accessor="place_3")
    big_bass = Column()
    club = Column()
    charity = Column()
    total = Column()

    class Meta:
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE


class Aoy(Table):
    angler = Column()
    total_points = Column()
    total_fish = Column()
    total_weight = Column()
    events = Column()

    class Meta:
        template_name = DEFAULT_TABLE_TEMPLATE


class BigBass(Table):
    angler = Column()
    weight = Column()
    tournament = Column()

    class Meta:
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE


class HeavyStringer(Table):
    angler = Column()
    weight = Column()
    fish = Column()
    tournament = Column()

    class Meta:
        orderable = False
        template_name = DEFAULT_TABLE_TEMPLATE
