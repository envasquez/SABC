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
    ForeignKey,
    TimeField,
    CharField,
    TextField,
    IntegerField,
    DecimalField,
    BooleanField,
    DateField,
    DO_NOTHING,
)
from django.urls import reverse

from users.models import Angler

from . import (
    LAKES,
    RULES,
    PAYOUT,
    WEIGH_IN,
    ENTRY_FEE,
    FEE_BREAKDOWN,
    ENTRY_FEE_DOLLARS,
    DEAD_FISH_PENALTY,
    BIG_BASS_BREAKDOWN,
    DEFAULT_PAID_PLACES,
)
from .exceptions import TournamentNotComplete, IncorrectTournamentType


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
        entry_fee (IntegerField) Description of the entry fee
        fee_breakdown (TextField) Description of how the payouts breakdown
        dead_fish_penalty (DecimalField) Decimal amount of weight penalized per fish
        big_bass_breakdown (TextField) Description of the big bass criteria
    """

    name = CharField(default="SABC Default Rules", max_length=100)
    fee = DecimalField(default=Decimal(str(ENTRY_FEE_DOLLARS)), max_digits=5, decimal_places=2)
    rules = TextField(default=RULES)
    payout = TextField(default=PAYOUT)
    weigh_in = TextField(default=WEIGH_IN)
    entry_fee = TextField(default=ENTRY_FEE)
    fee_breakdown = TextField(default=FEE_BREAKDOWN)
    big_bass_breakdown = TextField(default=BIG_BASS_BREAKDOWN)
    dead_fish_penalty = DecimalField(
        default=Decimal(str(DEAD_FISH_PENALTY)), max_digits=4, decimal_places=2
    )

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

        Args:
            tournament (Tournament) The tournament to calculate points for.
        Raises:
            TournamentNotComplete if the tournament is not completed.
            IncorrectTournamentType if the tournament does not count for AoY points.
        """
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")
        if not tournament.points:
            raise IncorrectTournamentType(f"{tournament.name} - not count for AoY points")

        for result in Result.objects.filter(tournament=tournament):
            result.points = 100 - (result.place_finish - 1)
            result.save()
        # Buy-ins get 2pts less than the last place physical tournament participant
        lowest_points = Result.objects.filter(tournament=tournament, buy_in=False).last().points
        buy_in_points = lowest_points - 2
        for result in Result.objects.filter(tournament=tournament, buy_in=True):
            result.points = buy_in_points
            result.save()

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
            { 'place_1': 100.00,
              'place_2': 100.00,
              'place_3': 100.00,
              'charity': 100.00,
              'big_bass': 100.00,
              'total': 500.00,
              'bb_cary_over: False}
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")

        bb_query = {"tournament": tournament, "big_bass_weight__gte": 5.0}
        bb_exists = Result.objects.filter(**bb_query).count() > 0
        num_anglers = Decimal(str(Result.objects.filter(tournament=tournament).count()))
        if tournament.multi_day:
            day_1 = Result.objects.filter(tournament=tournament, day_num=1).count()
            day_2 = Result.objects.filter(tournament=tournament, day_num=2).count()
            num_anglers = Decimal(str(day_1 + day_2))

        return {
            "club": Decimal("3.00") * num_anglers,
            "total": Decimal(str(tournament.fee)) * num_anglers,
            "place_1": Decimal("6.00") * num_anglers,
            "place_2": Decimal("4.00") * num_anglers,
            "place_3": Decimal("3.00") * num_anglers,
            "charity": Decimal("2.00") * num_anglers,
            "big_bass": Decimal("2.00") * num_anglers,
            "bb_carry_over": not bb_exists,
        }

    def set_individual_places(self, tournament):
        """Sets the place_finish attribute for a completed individual tournament
        Args:
            tournament (Tournament) The tournament to get winners from
        Raises:
            IncorrectTournamentType if the tournament is a Team tournament, not an individual one
        """

        def _set_places(query):
            """Sets the place_fish attribute for a given query"""
            place = 1
            for idx, result in enumerate(query, start=1):
                result.place_finish = place
                result.save()
                same_wt = result.total_weight == query[idx - 1].total_weight
                paid_place = idx <= tournament.paid_places
                if any([not same_wt, paid_place, not result.buy_in]):
                    place += 1

        if tournament.team:
            msg = f"{tournament} is a Team Tournament - try calling Tournament.set_team_places()"
            raise IncorrectTournamentType(msg)
        #
        # Set Individual Places
        #
        if not tournament.multi_day:
            _set_places(query=Result.objects.filter(tournament=tournament))
            tournament.complete = True
            tournament.save()
            return

        # Create a MultidayResult to determine the overall tournament winner
        day_1 = Result.objects.filter(tournament=tournament, day_num=1)
        for result in day_1:
            kwargs = {
                "tournament": tournament,
                "day_1": result,
                "day_2": Result.objects.get(angler=result.angler, day_num=2, tournament=tournament),
            }
            MultidayResult.objects.create(**kwargs).save()
        _set_places(query=MultidayResult.objects.filter(tournament=tournament))

    def set_team_places(self, tournament):
        """Sets the place_finish for a TeamResult"""
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")
        if not tournament.team:
            raise IncorrectTournamentType(f"Error: {tournament} is not a Team Tournament")

    def get_big_bass_winner(self, tournament):
        """Returns the Result object that contains the big bass winner
        Args:
            tournament (Tournament) The tournament to get the big bass winner for
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")


class Tournament(Model):
    """Tournament model

    Attributes:
        name (CharField) Name of the tournament.
        fee (DecimalField) Entry fee amount.
        date (DateField) Start date of the tournament.
        team (BooleanField) True if the tournament is a team tournament False otherwise.
        lake (CharField) Lake on which the event will take place.
        rules (ForeignKey) RuleSet to be used for this event.
        start (TimeField) Tournament start time.
        finish (TimeField) Tournament end time.
        points (BooleanField) True if the tournament counts towards AoY points.
        complete (BooleanField) True if the tournament is over, False otherwise.
        ramp_url (CharField) Google maps embedable link for weigh-in location.
        limit_num (IntegerField) The number of weighed fish that comprise a limit.
        multi_day (BooleanField) True if num_days > 1 False otherwise.
        description (TextField) A description of the tournament details.
        facebook_url (CharField) URL to the Facebok even or page.
        instagram_url (CharField) URL to the Instagram event or page.

        objects = Manager() Manager of objects (i.e. Tournament.objects.<something>)
        results = TournamentManager() Manager of results (i.e. Tournament.results.<something>)
    """

    name = CharField(default=f"Event #{strftime('%m')} {strftime('%Y')}", max_length=512)
    fee = DecimalField(default=Decimal("20.00"), max_digits=6, decimal_places=2)
    date = DateField(null=True)
    team = BooleanField(default=True)
    lake = CharField(default="TBD", null=False, blank=False, max_length=100, choices=LAKES)
    rules = ForeignKey(RuleSet, null=True, on_delete=DO_NOTHING)
    start = TimeField(blank=True, null=True)
    finish = TimeField(blank=True, null=True)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
    ramp_url = CharField(default="", max_length=1024, blank=True)
    limit_num = IntegerField(default=5)
    multi_day = BooleanField(default=False)
    paid_places = IntegerField(default=DEFAULT_PAID_PLACES)
    description = TextField(default="TBD")
    facebook_url = CharField(max_length=1024, blank=True)
    instagram_url = CharField(max_length=1024, blank=True)

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
    """This model represents an individuals performance in a tournament


    Attributes:
        angler (ForeignKey) The Angler object these results are associated with.
        buy_in (BooleanField) True if the angler bougt in, False otherwise.
        points (IntegerField) The number of points awarded from the tournament.
        day_num (IntegerField) Day number results for the tournament (default=1).
        tournament (ForeignKey) The tournament these results are associated with.
        place_finish (IntegerField) The place number the results finish overall.
        num_fish (IntegerField) The number of fish brought to the scales (weighed).
        total_weight (DecimalField) The total amount of fish weighed (in pounds).
        num_fish_dead (IntegerField) Number of fish weighed that were dead.
        penalty_weight (DecimalField) The total amount of weight in penalty.
        num_fish_alive (IntegerField) Number of fish weighed that were alive.
        big_bass_weight (DecimalField) The weight of the biggest bass weighed.
    """

    class Meta:
        """Meta class to ensure ordering of results by the largest:
        total_weight, big_bass_weight, and number of fish_weighed

        This is essentially our tie breaker process implemented with Django query
        """

        ordering = ("place_finish", "-total_weight", "-big_bass_weight", "-num_fish")

    angler = ForeignKey(Angler, null=True, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False, null=False, blank=False)
    points = IntegerField(default=0, null=True, blank=True)
    day_num = IntegerField(default=1)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING, null=False, blank=False)
    place_finish = IntegerField(default=0)
    num_fish = IntegerField(default=0, null=False, blank=False)
    total_weight = DecimalField(
        default=Decimal("0.00"), null=False, blank=False, max_digits=5, decimal_places=2
    )
    num_fish_dead = IntegerField(default=0, null=False, blank=False)
    num_fish_alive = IntegerField(default=0, null=True, blank=True)
    penalty_weight = DecimalField(
        default=Decimal("0.00"), null=True, blank=True, max_digits=5, decimal_places=2
    )
    big_bass_weight = DecimalField(
        default=Decimal("0.00"), null=True, blank=True, max_digits=4, decimal_places=2
    )

    def __str__(self):
        """String representation of a Result object"""
        place = f"{self.place_finish}" if self.tournament.complete else ""
        points = f"{self.points} Points" if self.tournament.complete else ""
        weight = f"{self.num_fish} fish {self.total_weight}lbs" if not self.buy_in else "Buy-in"
        big_bass = f"{self.big_bass_weight}lb big bass" if not self.buy_in else ""
        day_number = f"{'Day: ' + self.day_num if self.tournament.multi_day else ''}"
        tournament = f"{self.tournament.name} Lake: {self.tournament.lake}"
        return (
            f"{place}. {self.angler.user.get_full_name()}"
            + f"| {tournament} | {weight} {big_bass} {points}{day_number}"
        )

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-add", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save the result"""
        if self.penalty_weight == Decimal("0.00"):  # In case it was not entered
            self.penalty_weight = Decimal(str(self.num_fish_dead)) * Decimal(
                str(self.tournament.rules.dead_fish_penalty)
            )
        self.num_fish_alive = self.num_fish - self.num_fish_dead
        self.total_weight = Decimal(str(self.total_weight)) - Decimal(str(self.penalty_weight))
        super().save(*args, **kwargs)


class MultidayResult(Model):
    """Creates a sum of two results from a multi-day tournament

    Attributes:
        tournament (ForeignKey)
        day_1 (ForeignKey) Result for day 1.
        day_2 (ForeignKey) Result for day 2.
        buy_in (BooleanField) True if the angler bougt in, False otherwise.
        place_finish (IntegerField) The place number the results finish overall.
        num_fish (IntegerField) The number of fish brought to the scales (weighed).
        total_weight (DecimalField) The total amount of fish weighed (in pounds).
        num_fish_dead (IntegerField) Number of fish weighed that were dead.
        num_fish_alive (IntegerField) Number of fish weighed that were alive.
        penalty_weight (DecimalField) The total amount of weight in penalty.
        big_bass_weight (DecimalField) The weight of the biggest bass weighed.
    """

    class Meta:
        """Meta class to ensure ordering of results by the largest:
        total_weight, big_bass_weight, and number of fish_weighed

        This is essentially our tie breaker process implemented with Django query
        """

        ordering = ("place_finish", "-total_weight", "-big_bass_weight", "-num_fish")

    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)
    day_1 = ForeignKey(Result, null=True, related_name="+", on_delete=DO_NOTHING)
    day_2 = ForeignKey(Result, null=True, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False)
    place_finish = IntegerField(default=0)
    num_fish = IntegerField(default=0)
    total_weight = DecimalField(default=Decimal("0.00"), max_digits=5, decimal_places=2)
    num_fish_dead = IntegerField(default=0)
    num_fish_alive = IntegerField(default=0)
    penalty_weight = DecimalField(default=Decimal("0.00"), max_digits=4, decimal_places=2)
    big_bass_weight = DecimalField(default=Decimal("0.00"), max_digits=4, decimal_places=2)

    def __str__(self):
        """String representation of a MultidayResult"""
        weight = f"{self.num_fish} fish {self.total_weight}lbs" if not self.buy_in else "Buy-in"
        big_bass = f"{self.big_bass_weight}lb big bass" if not self.buy_in else ""
        tournament = f"{self.tournament.name} Lake: {self.tournament.lake}"
        return f"{self.day_1.angler.user.get_full_name()} | {tournament} | {weight} {big_bass}"

    def save(self, *args, **kwargs):
        """Saves a MultidayResult object

        Args:
            *args (list) A list of arguments
            **kwargs (dict) A dictionary of keyword arguments
        """
        if all([self.day_1.buy_in, self.day_2.buy_in]):
            self.buy_in = True
        if not self.buy_in:
            self.num_fish = self.day_1.num_fish + self.day_2.num_fish
            self.total_weight = self.day_1.total_weight + self.day_2.total_weight
            self.num_fish_dead = self.day_1.num_fish_dead + self.day_2.num_fish_dead
            self.penalty_weight = self.day_1.penalty_weight + self.day_2.penalty_weight
            self.num_fish_alive = self.day_1.num_fish_alive + self.day_2.num_fish_alive
            self.big_bass_weight = max([self.day_1.big_bass_weight, self.day_2.big_bass_weight])

        super().save(*args, **kwargs)


class TeamResult(Model):
    """This model represents a team result in a tournament.

    Attributes:
        boater (ForeignKey) Pointer to the Angler that was the boater.
        result_1 (ForeignKey) Result for Angler #1.
        result_2 (ForeignKey) Result for Angler #2.
        place_finish (IntegerField) The place number the results finish overall.
    """

    boater = ForeignKey(Angler, related_name="+", on_delete=DO_NOTHING)
    result_1 = ForeignKey(Result, null=True, blank=True, on_delete=DO_NOTHING)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=DO_NOTHING)
    place_finish = IntegerField(default=0)

    def __str__(self):
        """String representation of a TeamResult"""
        angler_1 = self.result_1.angler.user.get_full_name()
        if self.result_2:
            angler_2 = self.result_2.angler.user.get_full_name()
            return f"Team: {angler_1} & {angler_2}"

        return f"Team: {angler_1} - SOLO"

    def get_absolute_url(self):
        """Returns the absolute url for this model"""
        return reverse("team-details", kwargs={"pk": self.id})
