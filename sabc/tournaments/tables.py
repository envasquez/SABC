"""Tables for tournament results data"""

from django_tables2.tables import Table
from django_tables2.columns import Column

from .models import Result, TeamResult

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


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
            "penalty_weight",
            "big_bass_weight",
            "total_weight",
            "points",
            "buy_in",
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
            "penalty_weight",
            "big_bass_weight",
            "total_weight",
        )


class TournamentSummary(Table):
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
