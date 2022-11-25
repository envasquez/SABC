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
