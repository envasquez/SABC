# -*- coding: utf-8 -*-
from typing import Type

from django_tables2.columns import Column, LinkColumn
from django_tables2.tables import Table
from django_tables2.utils import A

from .models.results import Result, TeamResult

DEFAULT_TABLE_TEMPLATE: str = "django_tables2/bootstrap4.html"


class EditableResultTable(Table):
    edit: LinkColumn = LinkColumn("result-update", text="edit", args=[A("pk")], orderable=False, empty_values=())
    delete: LinkColumn = LinkColumn("result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=())
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class ResultTable(Table):
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class EditableTeamResultTable(Table):
    delete: LinkColumn = LinkColumn(
        "teamresult-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )

    class Meta:
        model: Type[TeamResult] = TeamResult
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = ("place_finish", "team_name", "num_fish", "big_bass_weight", "total_weight")


class TeamResultTable(Table):
    class Meta:
        model: Type[TeamResult] = TeamResult
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = ("place_finish", "team_name", "num_fish", "big_bass_weight", "total_weight")


class EditableBuyInTable(Table):
    edit: LinkColumn = LinkColumn("result-update", text="edit", args=[A("pk")], orderable=False, empty_values=())
    delete: LinkColumn = LinkColumn("result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=())
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = ("place_finish", "first_name", "last_name", "points")


class BuyInTable(Table):
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = ("place_finish", "first_name", "last_name", "points")


class EditableDQTable(Table):
    edit: LinkColumn = LinkColumn("result-update", text="edit", args=[A("pk")], orderable=False, empty_values=())
    delete: LinkColumn = LinkColumn("result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=())
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class DQTable(Table):
    first_name: Column = Column(accessor="angler.user.first_name")
    last_name: Column = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "num_fish",
            "total_weight",
            "points",
            "big_bass_weight",
        )


class TournamentSummaryTable(Table):
    total_fish: Column = Column()
    total_weight: Column = Column()
    limits: Column = Column()
    zeros: Column = Column()
    buy_ins: Column = Column()
    big_bass: Column = Column()
    heavy_stringer: Column = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class PayoutSummary(Table):
    first: Column = Column(accessor="place_1")
    second: Column = Column(accessor="place_2")
    third: Column = Column(accessor="place_3")
    big_bass: Column = Column()
    club: Column = Column()
    charity: Column = Column()
    total: Column = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class Aoy(Table):
    angler: Column = Column()
    total_points: Column = Column()
    total_fish: Column = Column()
    total_weight: Column = Column()
    events: Column = Column()

    class Meta:
        template_name: str = DEFAULT_TABLE_TEMPLATE


class BigBass(Table):
    angler: Column = Column()
    weight: Column = Column()
    tournament: Column = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class HeavyStringer(Table):
    angler: Column = Column()
    weight: Column = Column()
    fish: Column = Column()
    tournament: Column = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
