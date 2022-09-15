# -*- coding: utf-8 -*-
"""SABC Models

This file contains the models used to track Tournament events and their Results for individual
and team tournaments.
"""
from __future__ import unicode_literals

from time import strftime
from decimal import Decimal

from django.db.models import (
    Model,
    Manager,
    TimeField,
    CharField,
    TextField,
    DateField,
    DO_NOTHING,
    ForeignKey,
    DecimalField,
    BooleanField,
    SmallIntegerField,
)
from django.urls import reverse

from users.models import Angler

from . import (
    LAKES,
    RULE_INFO,
    PAYOUT,
    WEIGH_IN,
    PAYMENT,
    FEE_BREAKDOWN,
    DEFAULT_END_TIME,
    ENTRY_FEE_DOLLARS,
    DEAD_FISH_PENALTY,
    DEFAULT_START_TIME,
    BIG_BASS_BREAKDOWN,
    DEFAULT_PAID_PLACES,
    DEFAULT_FACEBOOK_URL,
    DEFAULT_INSTAGRAM_URL,
    get_last_sunday,
    get_weight_from_length,
)


class RuleSet(Model):
    """Rules model for tournaments

    Rules are typically only used for views. They don't change much - but if they do, we should
    store them in a database and reuse them where possible.

    Attributes:
        name (CharField) The name of the rule set
        fee (DecimalField) The dollar amount of the entry fee
        rules (TextField) Description of the rules to be followed
        payout (TextField) Description of the payouts
        weigh_in (TextField) Description of the weigh-in procedures
        entry_fee (SmallIntegerField) Description of the entry fee
        fee_breakdown (TextField) Description of how the payouts breakdown
        dead_fish_penalty (DecimalField) Decimal amount of weight penalized per fish
        big_bass_breakdown (TextField) Description of the big bass criteria
    """

    name = CharField(default="SABC Default Rules", max_length=100)
    fee = DecimalField(default=ENTRY_FEE_DOLLARS, max_digits=5, decimal_places=2)
    rules = TextField(default=RULE_INFO)
    payout = TextField(default=PAYOUT)
    weigh_in = TextField(default=WEIGH_IN)
    entry_fee = TextField(default=PAYMENT)
    fee_breakdown = TextField(default=FEE_BREAKDOWN)
    dead_fish_penalty = DecimalField(default=DEAD_FISH_PENALTY, max_digits=5, decimal_places=2)
    big_bass_breakdown = TextField(default=BIG_BASS_BREAKDOWN)

    def save(self, *args, **kwargs):
        """Saves a the current instance of a rule set

        Args:
            *args (list) Any arguments/attributes
            **kwargs (dict) Any keyword arguments/attributes
        """
        if not self.name:
            self.name = f"RuleSet-{self.id}"
        super().save(*args, **kwargs)

    def __str__(self):
        """Returns a string representation of a RuleSet (its name)"""
        return self.name


class TournamentManager(Manager):
    """A manager for tournament results.

    We can use a TournamenManager to execute queries for results of a tournament and transforming
    it to data that can be used in the views.

    Attributes:
        Tournament.results.set_aoy_points(Tournament) (#57)
        Tournament.results.get_payouts(Tournament) (#58)
        Tournament.results.set_individual_places(Tournament) (#60)
        Tournament.results.set_team_places(Tournament) (#59)
        Tournament.results.get_big_bass_winner(Tournament) (#61)
        Tournament.results.get_summary(Tournament) (#62)
    """

    def set_aoy_points(self, tournament):
        """Calculates the AoY points for a tournament and sets the points attribute for each Result.

        1st = 100 - (1 - 1) = 100
        2nd = 100 - (2 - 1) = 99
        3rd = 100 - (3 - 1) = 98
        ... and so on ...
        NOTE: Buy-ins receive 2 less points than the last place_finish of anglers that weighed
              in fish.
              Guests, do NOT recieve AoY points

        Args:
            tournament (Tournament) The tournament to calculate points for.
        """

        def _set_member_pts():
            """Set points for members who weighed in fish"""
            points = tournament.max_points
            member_results = Result.objects.filter(
                tournament=tournament,
                buy_in=False,
                angler__type="member",
                num_fish__gt=0,
                day_num=1,
            ).order_by("place_finish")
            for idx, result in enumerate(member_results):
                result.points = points
                result.save()
                prev_wt = member_results[idx - 1].total_weight if idx > 0 else 0
                prev_finish = member_results[idx - 1].place_finish if idx > 0 else 0
                tie_exists = prev_finish == result.place_finish and prev_wt == result.total_weight
                if not tie_exists:
                    points -= 1

        def _set_zeroed_pts():
            """Set points for members who fished, but didn't weigh in any fish"""
            # Anglers that didn't weigh in any fish get lowest_pts - 2
            zeroed_results = Result.objects.filter(
                tournament=tournament, buy_in=False, angler__type="member", num_fish=0, day_num=1
            )
            for result in zeroed_results:
                result.points = lowest_points - 2
                result.save()

        def _set_buy_in_pts():
            """Set points for members who bought in"""
            for result in Result.objects.filter(tournament=tournament, day_num=1, buy_in=True):
                result.points = lowest_points - 4
                result.save()

        self.set_places(tournament)
        _set_member_pts()
        lowest_points = (
            Result.objects.filter(
                tournament=tournament, day_num=1, angler__type="member", points__gt=0
            )
            .order_by("points")
            .first()
            .points
        )
        _set_zeroed_pts()
        _set_buy_in_pts()

    def get_payouts(self, tournament):
        """Calculates amount of funds to be applied to the club, charity and winners

        From the wiki ...
        TOTAL_RESULT_COUNT = NUM_WT_RESULTS + NUM_BUY_IN_RESULTS
        1ST_PLACE = 6 * TOTAL_RESULT_COUNT
        2ND_PLACE = 4 * TOTAL_RESULT_COUNT
        3RD_PLACE = 3 * TOTAL_RESULT_COUNT
        CLUB_FUNDS = 3 * TOTAL_RESULT_COUNT
        BIG_BASS_POT = 2 * TOTAL_RESULT_COUNT
        CHARITY_FUNDS = 2 * TOTAL_RESULT_COUNT

        Args:
            tournament (Tournament) The tournament to calculate payouts for
        Returns:
            A dict mapping the amounts paid to places, chairty and big bass
            Example:
            { 'place_1': Decimal("100.00"),
              'place_2': Decimal("100.00"),
              'place_3': Decimal("100.00"),
              'charity': Decimal("100.00"),
              'big_bass': Decimal("100.0")",
              'total': Decimal("500.00"),
              'bb_cary_over: False}
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        bb_query = {"tournament": tournament, "big_bass_weight__gte": 5.0}
        bb_exists = Result.objects.filter(**bb_query).count() > 0
        num_anglers = Result.objects.filter(tournament=tournament).count()
        if tournament.multi_day:
            day_1 = Result.objects.filter(tournament=tournament, day_num=1).count()
            day_2 = Result.objects.filter(tournament=tournament, day_num=2).count()
            num_anglers = day_1 + day_2

        return {
            "club": Decimal("3.00") * num_anglers,
            "total": tournament.fee * num_anglers,
            "place_1": Decimal("6.00") * num_anglers,
            "place_2": Decimal("4.00") * num_anglers,
            "place_3": Decimal("3.00") * num_anglers,
            "charity": Decimal("2.00") * num_anglers,
            "big_bass": Decimal("2.00") * num_anglers,
            "bb_carry_over": not bb_exists,
        }

    def set_places(self, tournament):
        """Sets the place_finish attribute for a complete tournament
        Args:
            tournament (Tournament) The tournament to get winners from
        """

        def _set_places(query):
            place = 1
            weighed_fish = [q for q in query if not q.buy_in and q.total_weight > Decimal("0.00")]
            for idx, result in enumerate(weighed_fish):
                result.place_finish = place
                result.save()
                tie = result.total_weight == query[idx - 1].total_weight if idx != 0 else -999
                if not tie or place < tournament.paid_places:
                    place += 1

            zero_fish = [q for q in query if not q.total_weight]
            for result in zero_fish:
                result.place_finish = place
                result.save()

            place += 1
            buy_ins = [q for q in query if q.buy_in]
            for result in buy_ins:
                result.place_finish = place
                result.save()

        def _set_multi_day_places():
            for day_1 in first_day:
                angler = day_1.angler
                day_2 = Result.objects.filter(
                    tournament=tournament, day_num=2, angler=angler
                ).first()
                MultidayResult.objects.create(
                    tournament=tournament, day_1=day_1, day_2=day_2
                ).save()
                _set_places(MultidayResult.objects.filter(tournament=tournament).order_by(*order))

        def _set_multi_day_team_places():
            for day_1 in TeamResult.objects.filter(tournament=tournament, day_num=1):
                boater = day_1.boater
                day_2 = TeamResult.objects.filter(
                    tournament=tournament, day_num=2, boater=boater
                ).first()
                MultidayTeamResult.objects.create(
                    tournament=tournament, day_1=day_1, day_2=day_2
                ).save()
                _set_places(
                    MultidayTeamResult.objects.filter(tournament=tournament).order_by(*order)
                )

        #
        # Set Places
        #
        order = ("-total_weight", "-big_bass_weight", "-num_fish")
        first_day = Result.objects.filter(tournament=tournament, day_num=1).order_by(*order)
        _set_places(first_day)
        if tournament.multi_day and not tournament.team:
            second_day = Result.objects.filter(tournament=tournament, day_num=2).order_by(*order)
            _set_places(second_day)
            _set_multi_day_places()
        elif tournament.team and not tournament.multi_day:
            _set_places(
                TeamResult.objects.filter(tournament=tournament, day_num=1).order_by(*order)
            )
        else:
            _set_multi_day_team_places()

        tournament.complete = True
        tournament.save()

    def get_big_bass_winner(self, tournament):
        """Returns the Result object that contains the big bass winner
        Args:
            tournament (Tournament) The tournament to get the big bass winner for
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        if not tournament.multi_day and not tournament.team:
            return (
                Result.objects.filter(tournament=tournament, big_bass_weight__gte=Decimal("5.00"))
                .order_by("-big_bass_weight")
                .first()
            )
        if not tournament.multi_day and tournament.team:
            return (
                TeamResult.objects.filter(
                    tournament=tournament, big_bass_weight__gte=Decimal("5.00")
                )
                .order_by("-big_bass_weight")
                .first()
            )
        if tournament.multi_day and not tournament.team:
            return (
                MultidayResult.objects.filter(
                    tournament=tournament, big_bass_weight__gte=Decimal("5.00")
                )
                .order_by("-big_bass_weight")
                .first()
            )
        return (
            MultidayTeamResult.objects.filter(
                tournament=tournament, big_bass_weight__gte=Decimal("5.00")
            )
            .order_by("-big_bass_weight")
            .first()
        )


class Tournament(Model):
    """This model represents a Tournament.

    Attributes:
        fee (DecimalField) Entry fee amount.
        name (CharField) Name of the tournament.
        date (DateField) Start date of the tournament.
        team (BooleanField) True if the tournament is a team tournament False otherwise.
        lake (CharField) Lake on which the event will take place.
        rules (ForeignKey) RuleSet to be used for this event.
        start (TimeField) Tournament start time.
        finish (TimeField) Tournament end time.
        points (BooleanField) True if the tournament counts towards AoY points.
        complete (BooleanField) True if the tournament is over, False otherwise.
        ramp_url (CharField) Google maps embedable link for weigh-in location.
        limit_num (SmallIntegerField) The number of weighed fish that comprise a limit.
        multi_day (BooleanField) True if num_days > 1 False otherwise.
        max_points (SmallIntegerField) Maximim number of points for AoY (default=100)
        description (TextField) A description of the tournament details.
        facebook_url (CharField) URL to the Facebok even or page.
        instagram_url (CharField) URL to the Instagram event or page.

        objects = Manager() Manager of objects (i.e. Tournament.objects.<something>)
        results = TournamentManager() Manager of results (i.e. Tournament.results.<something>)
    """

    fee = DecimalField(default=Decimal("20.00"), max_digits=5, decimal_places=2)
    name = CharField(default=f"Event #{strftime('%m')} {strftime('%Y')}", max_length=512)
    date = DateField(null=False, blank=False, default=get_last_sunday)
    team = BooleanField(default=True)
    lake = CharField(default="TBD", null=False, blank=False, max_length=100, choices=LAKES)
    rules = ForeignKey(RuleSet, null=True, blank=True, on_delete=DO_NOTHING)
    paper = BooleanField(default=False)
    start = TimeField(blank=False, null=False, default=DEFAULT_START_TIME)
    finish = TimeField(blank=False, null=False, default=DEFAULT_END_TIME)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
    ramp_url = CharField(default="", max_length=1024, blank=True)
    limit_num = SmallIntegerField(default=5)
    multi_day = BooleanField(default=False)
    max_points = SmallIntegerField(default=100)
    paid_places = SmallIntegerField(default=DEFAULT_PAID_PLACES)
    description = TextField(default="TBD")
    facebook_url = CharField(max_length=512, default=DEFAULT_FACEBOOK_URL)
    instagram_url = CharField(max_length=512, default=DEFAULT_INSTAGRAM_URL)

    objects = Manager()
    results = TournamentManager()

    def __str__(self):
        """Return the name of the tournament"""
        return str(self.name)

    def get_absolute_url(self):
        """Get the absolute url of the tournament details"""
        return reverse("tournament-details", kwargs={"pk": self.pk})

    def save(self, *args, **kwargs):
        """Save the tournament"""
        self.ramp_url = self.ramp_url.replace('height="450"', 'height="350"')
        if not self.rules:
            self.rules = RuleSet.objects.create()

        super().save(*args, **kwargs)


# pylint: disable=too-many-instance-attributes
class Result(Model):
    """This model represents an individuals performance in a tournament.


    Attributes:
        angler (ForeignKey) The Angler object these results are associated with.
        buy_in (BooleanField) True if the angler bougt in, False otherwise.
        points (SmallIntegerField) The number of points awarded from the tournament.
        day_num (SmallIntegerField) Day number results for the tournament (default=1).
        tournament (ForeignKey) The tournament these results are associated with.
        place_finish (SmallIntegerField) The place number the results finish overall.
        num_fish (SmallIntegerField) The number of fish brought to the scales (weighed).
        total_weight (DecimalField) The total amount of fish weighed (in pounds).
        num_fish_dead (SmallIntegerField) Number of fish weighed that were dead.
        penalty_weight (DecimalField) The total amount of weight in penalty.
        num_fish_alive (SmallIntegerField) Number of fish weighed that were alive.
        big_bass_weight (DecimalField) The weight of the biggest bass weighed.
    """

    angler = ForeignKey(Angler, null=True, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False, null=False, blank=False)
    points = SmallIntegerField(default=0, null=True, blank=True)
    day_num = SmallIntegerField(default=1)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING, null=False, blank=False)
    place_finish = SmallIntegerField(default=0)
    num_fish = SmallIntegerField(default=0, null=False, blank=False)
    total_weight = DecimalField(
        default=Decimal("0.00"), null=False, blank=False, max_digits=5, decimal_places=2
    )
    num_fish_dead = SmallIntegerField(default=0, null=False, blank=False)
    num_fish_alive = SmallIntegerField(default=0, null=True, blank=True)
    penalty_weight = DecimalField(
        default=Decimal("0.00"), null=True, blank=True, max_digits=5, decimal_places=2
    )
    big_bass_weight = DecimalField(
        default=Decimal("0.00"), null=True, blank=True, max_digits=5, decimal_places=2
    )

    def __str__(self):
        """String representation of a Result object"""
        place = f"{self.place_finish}."
        weight = f"{self.num_fish} @ {self.total_weight}lbs"
        points = f"{self.points} Points"
        if self.buy_in:
            weight = "Buy-in N/A lbs"
            big_bass = "N/A lb BB"
        big_bass = f"{self.big_bass_weight}lb BB"
        day_number = f"{'Day: ' + str(self.day_num) if self.tournament.multi_day else ''}"

        return (
            f"{place}{self.angler}{' ' * (30 - len(str(self.angler)))}"
            f"{weight}\t{big_bass}\t{points}\t{day_number}"
        )

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-create", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save the result"""
        if self.penalty_weight:
            self.penalty_weight = self.num_fish_dead * self.tournament.rules.dead_fish_penalty
        self.total_weight = Decimal(str(self.total_weight - self.penalty_weight))
        self.num_fish_alive = self.num_fish - self.num_fish_dead
        self.big_bass_weight = self.big_bass_weight

        super().save(*args, **kwargs)


class PaperResult(Result):
    """This model represents a Paper Tournament result.

    Attributes:
        fish1_wt (DecimalField) Length of fish1.
        fish2_wt (DecimalField) Length of fish2.
        fish3_wt (DecimalField) Length of fish3.
        fish4_wt (DecimalField) Length of fish4.
        fish5_wt (DecimalField) Length of fish4.
        fish1_len (DecimalField) Weight of fish1.
        fish2_len (DecimalField) Weight of fish2.
        fish3_len (DecimalField) Weight of fish3.
        fish4_len (DecimalField) Weight of fish4.
        fish5_len (DecimalField) Weight of fish5.
    """

    fish1_wt = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish2_wt = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish3_wt = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish4_wt = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish5_wt = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish1_len = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish2_len = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish3_len = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish4_len = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)
    fish5_len = DecimalField(default=Decimal("0.00"), decimal_places=2, max_digits=5)

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-create", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save the result"""
        self.fish1_wt = Decimal(str(get_weight_from_length(self.fish1_len)))
        self.fish2_wt = Decimal(str(get_weight_from_length(self.fish2_len)))
        self.fish3_wt = Decimal(str(get_weight_from_length(self.fish3_len)))
        self.fish4_wt = Decimal(str(get_weight_from_length(self.fish4_len)))
        self.fish5_wt = Decimal(str(get_weight_from_length(self.fish5_len)))
        self.total_weight = sum(
            [self.fish1_wt, self.fish2_wt, self.fish3_wt, self.fish4_wt, self.fish5_wt]
        )
        big_fish = [
            fish
            for fish in [self.fish1_wt, self.fish2_wt, self.fish3_wt, self.fish4_wt, self.fish5_wt]
            if fish >= Decimal("5.00")
        ]
        if any(big_fish):
            self.big_bass_weight = max(big_fish)

        super().save(*args, **kwargs)


class MultidayResult(Model):
    """Creates a sum of two results from a multi-day tournament

    Attributes:
        tournament (ForeignKey)
        day_1 (ForeignKey) Result for day 1.
        day_2 (ForeignKey) Result for day 2.
        buy_in (BooleanField) True if the angler bougt in, False otherwise.
        place_finish (SmallIntegerField) The place number the results finish overall.
        num_fish (SmallIntegerField) The number of fish brought to the scales (weighed).
        total_weight (DecimalField) The total amount of fish weighed (in pounds).
        num_fish_dead (SmallIntegerField) Number of fish weighed that were dead.
        num_fish_alive (SmallIntegerField) Number of fish weighed that were alive.
        penalty_weight (DecimalField) The total amount of weight in penalty.
        big_bass_weight (DecimalField) The weight of the biggest bass weighed.
    """

    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)
    day_1 = ForeignKey(Result, null=True, related_name="+", on_delete=DO_NOTHING)
    day_2 = ForeignKey(Result, null=True, on_delete=DO_NOTHING)

    buy_in = BooleanField(default=False, null=False, blank=False)
    num_fish = SmallIntegerField(default=0)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    num_fish_dead = SmallIntegerField(default=0)
    num_fish_alive = SmallIntegerField(default=0)
    penalty_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    big_bass_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)

    def __str__(self):
        """String representation of a MultidayResult"""
        name = self.day_1.angler
        place = f"{self.place_finish}."
        weight = f"2 day total: {self.total_weight}lbs"
        num_fish = f"{self.num_fish} fish"
        big_bass = f"{self.big_bass_weight}lb big bass"

        return (
            f"{place}{name}{' ' * (30 - len(str(name)))}"
            f"2 day total: {num_fish}: {weight}\t\t{big_bass}"
        )

    def save(self, *args, **kwargs):
        """Saves a MultidayResult object

        Args:
            *args (list) A list of arguments
            **kwargs (dict) A dictionary of keyword arguments
        """
        if self.day_2:
            self.num_fish = self.day_1.num_fish + self.day_2.num_fish
            self.total_weight = self.day_1.total_weight + self.day_2.total_weight
            self.num_fish_dead = self.day_1.num_fish_dead + self.day_2.num_fish_dead
            self.penalty_weight = self.day_1.penalty_weight + self.day_2.penalty_weight
            self.num_fish_alive = self.day_1.num_fish_alive + self.day_2.num_fish_alive
            self.big_bass_weight = max([self.day_1.big_bass_weight, self.day_2.big_bass_weight])
        else:
            for attr in [
                "buy_in",
                "num_fish",
                "total_weight",
                "big_bass_weight",
                "num_fish_alive",
                "num_fish_dead",
                "penalty_weight",
            ]:
                setattr(self, attr, getattr(self.day_1, attr))

        super().save(*args, **kwargs)


class TeamResult(Model):
    """This model represents a team result in a tournament.

    Attributes:
        boater (ForeignKey) Pointer to the Angler that was the boater.
        result_1 (ForeignKey) Result for Angler #1.
        result_2 (ForeignKey) Result for Angler #2.
        tournament (ForeignKey) Pointer to the tournament for this TeamResult
        num_fish (SmallIntegerField) Total number of fish wieghed in.
        place_finish (SmallIntegerField) The place number the results finish overall.
        total_weight (DecimalField) The total team weight.
        num_fish_dead (SmallIntegerField) The total number of fish dead.
        num_fish_alive (SmallIntegerField) The total number of fish alive.
        penalty_weight (DecimalField) The penalty weight multiplier.
        big_bass_weight (DecimalField) The weight of the biggest bass caught by the team.
    """

    boater = ForeignKey(Angler, related_name="+", on_delete=DO_NOTHING)
    result_1 = ForeignKey(Result, null=True, blank=True, on_delete=DO_NOTHING)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=DO_NOTHING)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)

    buy_in = BooleanField(default=False, null=False, blank=False)
    day_num = SmallIntegerField(default=1)
    num_fish = SmallIntegerField(default=0)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    num_fish_dead = SmallIntegerField(default=0)
    num_fish_alive = SmallIntegerField(default=0)
    penalty_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    big_bass_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)

    def __str__(self):
        """String representation of a TeamResult"""
        name = f"Team: {self.result_1.angler} - SOLO"
        if self.result_2:
            name = f"Team: {self.result_1.angler} & {self.result_2.angler}"
        place = f"{self.place_finish}."
        weight = f"{self.num_fish} @ {self.total_weight}lbs"
        if self.buy_in:
            weight = "Buy-in N/A lbs"
            big_bass = "N/A lb BB"
        big_bass = f"{self.big_bass_weight}lb BB"
        day_number = f"{'Day: ' + str(self.day_num) if self.tournament.multi_day else ''}"

        return f"{place}{name}{' ' * (60 - len(str(name)))}{weight}\t\t{big_bass}\t{day_number}"

    def get_absolute_url(self):
        """Returns the absolute url for this model"""
        return reverse("team-details", kwargs={"pk": self.id})

    def save(self, *args, **kwargs):
        """Saves a MultidayResult object

        Args:
            *args (list) A list of arguments
            **kwargs (dict) A dictionary of keyword arguments
        """
        if self.result_2:
            self.num_fish = sum([self.result_1.num_fish, self.result_2.num_fish])
            self.total_weight = sum([self.result_1.total_weight, self.result_2.total_weight])
            self.num_fish_dead = sum([self.result_1.num_fish, self.result_2.num_fish_dead])
            self.penalty_weight = sum([self.result_1.penalty_weight, self.result_2.penalty_weight])
            self.num_fish_alive = sum([self.result_1.num_fish_alive, self.result_2.num_fish_alive])
            self.big_bass_weight = max(
                [self.result_1.big_bass_weight, self.result_2.big_bass_weight]
            )
        else:
            for attr in [
                "buy_in",
                "num_fish",
                "total_weight",
                "big_bass_weight",
                "num_fish_alive",
                "num_fish_dead",
                "penalty_weight",
            ]:
                setattr(self, attr, getattr(self.result_1, attr))

        super().save(*args, **kwargs)


class MultidayTeamResult(Model):
    """This model represents a MultidayTeamResult

    Attributes:
        day_1 (ForeignKey) Day one TeamResult.
        day_2 (ForeignKey) Day two TeamResult.
        tournament (ForeignKey) The tournment related to this result.
        buy_in (BooleanField) Whether or not the result is a buy-in.
        num_fish (SmallIntegerField) Number of fish weiged in.
        place_finish (SmallIntegerField) The place finish for this result.
        total_weight (DecimalField) Total weight for the team, both days.
        num_fish_dead (SmallIntegerField) Total number of fish dead.
        num_fish_alive (SmallIntegerField) Total number of fish alive.
        penalty_weight (DecimalField) The penalty weight multiplier.
        big_bass_weight (DecimalField) Largest bass caught over both days for the team.
    """

    day_1 = ForeignKey(TeamResult, null=True, related_name="+", on_delete=DO_NOTHING)
    day_2 = ForeignKey(TeamResult, null=True, on_delete=DO_NOTHING)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)

    buy_in = BooleanField(default=False, null=False, blank=False)
    num_fish = SmallIntegerField(default=0)
    place_finish = SmallIntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    num_fish_dead = SmallIntegerField(default=0)
    num_fish_alive = SmallIntegerField(default=0)
    penalty_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    big_bass_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)

    def __str__(self):
        name = f"Team: {self.day_1.result_1.angler} - SOLO"
        if self.day_2:
            name = f"Team: {self.day_1.result_1.angler} & {self.day_2.result_1.angler}"
        place = f"{self.place_finish}."
        num_fish = f"{self.num_fish} fish"
        big_bass = f"{self.big_bass_weight}lb big bass"
        weight = f"2 day total: {self.total_weight}lbs"

        return f"{place}{name}{' ' * (60 - len(str(name)))} {num_fish}: {weight}\t\t{big_bass}"

    def save(self, *args, **kwargs):
        """Saves a MultidayResult object

        Args:
            *args (list) A list of arguments
            **kwargs (dict) A dictionary of keyword arguments
        """
        if self.day_2:
            self.num_fish = sum([self.day_1.num_fish, self.day_2.num_fish])
            self.total_weight = sum([self.day_1.total_weight, self.day_2.total_weight])
            self.num_fish_dead = sum([self.day_1.num_fish, self.day_2.num_fish_dead])
            self.penalty_weight = sum([self.day_1.penalty_weight, self.day_2.penalty_weight])
            self.num_fish_alive = sum([self.day_1.num_fish_alive, self.day_2.num_fish_alive])
            self.big_bass_weight = max([self.day_1.big_bass_weight, self.day_1.big_bass_weight])
        else:
            for attr in [
                "buy_in",
                "num_fish",
                "total_weight",
                "big_bass_weight",
                "num_fish_alive",
                "num_fish_dead",
                "penalty_weight",
            ]:
                setattr(self, attr, getattr(self.day_1, attr))

        super().save(*args, **kwargs)
