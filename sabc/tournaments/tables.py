# -*- coding: utf-8 -*-
from typing import Type

from django_tables2.utils import A
from django_tables2.tables import Table
from django_tables2.columns import Column, LinkColumn

from .models.results import Result, TeamResult

DEFAULT_TABLE_TEMPLATE: str = "django_tables2/bootstrap4.html"


class EditableResultTable(Table):
    delete: Type[LinkColumn] = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

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
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

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
    delete: Type[LinkColumn] = LinkColumn(
        "teamresult-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )

    class Meta:
        model: Type[TeamResult] = TeamResult
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "team_name",
            "num_fish",
            "big_bass_weight",
            "total_weight",
        )


class TeamResultTable(Table):
    class Meta:
        model: Type[TeamResult] = TeamResult
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "team_name",
            "num_fish",
            "big_bass_weight",
            "total_weight",
        )


class EditableBuyInTable(Table):
    delete: Type[LinkColumn] = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "points",
        )


class BuyInTable(Table):
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

    class Meta:
        model: Type[Result] = Result
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
        fields: tuple = (
            "place_finish",
            "first_name",
            "last_name",
            "points",
        )


class EditableDQTable(Table):
    delete: Type[LinkColumn] = LinkColumn(
        "result-delete", text="delete", args=[A("pk")], orderable=False, empty_values=()
    )
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

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
    first_name: Type[Column] = Column(accessor="angler.user.first_name")
    last_name: Type[Column] = Column(accessor="angler.user.last_name")

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
    total_fish: Type[Column] = Column()
    total_weight: Type[Column] = Column()
    limits: Type[Column] = Column()
    zeros: Type[Column] = Column()
    buy_ins: Type[Column] = Column()
    big_bass: Type[Column] = Column()
    heavy_stringer: Type[Column] = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class PayoutSummary(Table):
    first: Type[Column] = Column(accessor="place_1")
    second: Type[Column] = Column(accessor="place_2")
    third: Type[Column] = Column(accessor="place_3")
    big_bass: Type[Column] = Column()
    club: Type[Column] = Column()
    charity: Type[Column] = Column()
    total: Type[Column] = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class Aoy(Table):
    angler: Type[Column] = Column()
    total_points: Type[Column] = Column()
    total_fish: Type[Column] = Column()
    total_weight: Type[Column] = Column()
    events: Type[Column] = Column()

    class Meta:
        template_name: str = DEFAULT_TABLE_TEMPLATE


class BigBass(Table):
    angler: Type[Column] = Column()
    weight: Type[Column] = Column()
    tournament: Type[Column] = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE


class HeavyStringer(Table):
    angler: Type[Column] = Column()
    weight: Type[Column] = Column()
    fish: Type[Column] = Column()
    tournament: Type[Column] = Column()

    class Meta:
        orderable: bool = False
        template_name: str = DEFAULT_TABLE_TEMPLATE
