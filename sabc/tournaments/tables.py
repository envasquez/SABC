import django_tables2 as tables

from .models import Result, TeamResult

DEFAULT_TABLE_TEMPLATE = "django_tables2/bootstrap4.html"


class ResultTable(tables.Table):
    """Table for displaying Officers

    Model Attributes:
        angler (ForeignKey) The Angler object these results are associated with.
        buy_in (BooleanField) True if the angler bougt in, False otherwise.
        points (SmallIntegerField) The number of points awarded from the tournament.
        num_fish (SmallIntegerField) The number of fish brought to the scales (weighed).
        tournament (ForeignKey) The tournament these results are associated with.
        place_finish (SmallIntegerField) The place number the results finish overall.
        total_weight (DecimalField) The total amount of fish weighed (in pounds).
        num_fish_dead (SmallIntegerField) Number of fish weighed that were dead.
        penalty_weight (DecimalField) The total amount of weight in penalty.
        num_fish_alive (SmallIntegerField) Number of fish weighed that were alive.
        big_bass_weight (DecimalField) The weight of the biggest bass weighed.
    """

    first_name = tables.Column(accessor="angler.user.first_name")
    last_name = tables.Column(accessor="angler.user.last_name")

    class Meta:
        """Default OfficerTable settings"""

        model = Result
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


class TeamResultTable(tables.Table):
    """Table for displaying Officers

    Model Attributes:
        boater (ForeignKey) Pointer to the Angler that was the boater.
        result_1 (ForeignKey) Result for Angler #1.
        result_2 (ForeignKey) Result for Angler #2.
        tournament (ForeignKey) Pointer to the tournament for this TeamResult
        num_fish (SmallIntegerField) Total number of fish wieghed in.
        team_name CharField(max_length=512, default="")
        place_finish (SmallIntegerField) The place number the results finish overall.
        total_weight (DecimalField) The total team weight.
        num_fish_dead (SmallIntegerField) The total number of fish dead.
        num_fish_alive (SmallIntegerField) The total number of fish alive.
        penalty_weight (DecimalField) The penalty weight multiplier.
        big_bass_weight (DecimalField) The weight of the biggest bass caught by the team.
    """

    class Meta:
        """Default OfficerTable settings"""

        model = TeamResult
        template_name = DEFAULT_TABLE_TEMPLATE

        fields = (
            "place_finish",
            "team_name",
            "num_fish" "penalty_weight",
            "big_bass_weight",
            "total_weight",
        )
