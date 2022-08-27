# -*- coding: utf-8 -*-
"""SABC Models

This file contains the models used to track Tournament events and their Results for individual
and team tournaments.
"""
from __future__ import unicode_literals

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
    FloatField,
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
    get_tournament_name,
    get_tournament_description,
    get_length_from_weight,
    get_weight_from_length,
)
from .exceptions import TournamentNotComplete, IncorrectTournamentType


class RuleSet(Model):
    """Rules model for tournaments

    Rules are typically only used for views. They don't change much - but if they do, we should
    store them in a database and reuse them where possible.

    Attributes:
        name (CharField) The name of the rule set
        fee (FloatField) The dollar amount of the entry fee
        rules (TextField) Description of the rules to be followed
        payout (TextField) Description of the payouts
        weigh_in (TextField) Description of the weigh-in procedures
        entry_fee (IntegerField) Description of the entry fee
        fee_breakdown (TextField) Description of how the payouts breakdown
        dead_fish_penalty (FloatField) Decimal amount of weight penalized per fish
        big_bass_breakdown (TextField) Description of the big bass criteria
    """

    name = CharField(default="SABC Default Rules", max_length=100, unique=True)
    fee = FloatField(default=ENTRY_FEE_DOLLARS)
    rules = TextField(default=RULES)
    payout = TextField(default=PAYOUT)
    weigh_in = TextField(default=WEIGH_IN)
    entry_fee = TextField(default=ENTRY_FEE)
    fee_breakdown = TextField(default=FEE_BREAKDOWN)
    big_bass_breakdown = TextField(default=BIG_BASS_BREAKDOWN)
    dead_fish_penalty = FloatField(default=DEAD_FISH_PENALTY)

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
        """Calculates the AoY points for a tournament and sets the points attribute for each Result
        1st = 100 - (1 - 1) = 100
        2nd = 100 - (2 - 1) = 99
        3rd = 100 - (3 - 1) = 98
        ... and so on ...
        For all anglers that did not weigh in fish, they receive 2 less points than the
        last place_finish of anglers that weighed in fish.

        Args:
            tournament (Tournament) The tournament to calculate points for
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")

    def get_payouts(self, tournament):
        """Calculates amount of funds to be applied to the club, charity and winners

        Args:
            tournament (Tournament) The tournament to calculate payouts for
        Returns:
            A dict mapping the amounts paid to places, chairty and big bass
            Example:
            { 'place_1': 100.00,
              'place_2': 100.00,
              'place_3': 100.00,
              'charity': 100.00,
              'big_bass': 100.00,}
        Raises:
            TournamentNotComplete if the tournament is not completed
        """
        if not tournament.complete:
            raise TournamentNotComplete(f"{tournament} is not complete!")

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

        # Set Individual Places
        if not tournament.multi_day:
            _set_places(query=Result.objects.filter(tournament=tournament))
            return

        # Create a MultidayResult to determine the overall tournament winner
        day_1 = Result.objects.filter(tournament=tournament, day_num=1)
        for result in day_1:
            kwargs = {
                "angler": result.angler,
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

    name = CharField(default=get_tournament_name(), max_length=512)
    fee = DecimalField(default=20, max_digits=7, decimal_places=2)
    date = DateField(null=True)
    team = BooleanField(default=True)
    lake = CharField(default="TBD", max_length=100, choices=LAKES)
    rules = ForeignKey(RuleSet, null=True, on_delete=DO_NOTHING)
    start = TimeField(blank=True, null=True)
    finish = TimeField(blank=True, null=True)
    points = BooleanField(default=True)
    complete = BooleanField(default=False)
    ramp_url = CharField(default="", max_length=1024, blank=True)
    limit_num = IntegerField(default=5)
    multi_day = BooleanField(default=False)
    paid_places = IntegerField(default=DEFAULT_PAID_PLACES)
    description = TextField(default=get_tournament_description())
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
        buy_in (BooleanField) True is the angler bougt in, False otherwise.
        points (IntegerField) The number of points awarded from the tournament.
        day_num (IntegerField) Day number results for the tournament (default=1).
        tournament (ForeignKey) The tournament these results are associated with.
        total_weight (FloatField) The total amount of fish weighed (in pounds).
        num_fish_dead (IntegerField) Number of fish weighed that were dead.
        num_fish_alive (IntegerField) Number of fish weighed that were alive.
        big_bass_weight (FloatField) The weight of the biggest bass weighed.
        penalty_weight (FloatField) The total amount of weight in penalty.
        num_fish_weighed (IntegerField) Number of fish weighed.
        fish_1_wt (FloatField) The weight of fish number 1.
        fish_1_len (FloatField) The length of fish number 1.
        fish_1_alive (BooleanField) True if a fish_1 is alive, False if it is dead.
        fish_2_wt (FloatField) The weight of fish number 2.
        fish_2_len (FloatField) The length of fish number 2.
        fish_2_alive (BooleanField) True if a fish_2 is alive, False if it is dead.
        fish_3_wt (FloatField) The weight of fish number 3.
        fish_3_len (FloatField) The length of fish number 3.
        fish_3_alive (BooleanField) True if a fish_3 is alive, False if it is dead.
        fish_4_wt (FloatField) The weight of fish number 4.
        fish_4_len (FloatField) The length of fish number 4.
        fish_4_alive (BooleanField) True if a fish_4 is alive, False if it is dead.
        fish_5_wt (FloatField) The weight of fish number 5.
        fish_5_len (FloatField) The length of fish number 5.
        fish_5_alive (BooleanField) True if a fish_5 is alive, False if it is dead.
    """

    class Meta:
        """Meta class to ensure ordering of results by the largest:
        total_weight, big_bass_weight, and number of fish_weighed

        This is essentially our tie breaker process implemented with Django query
        """

        ordering = ("-total_weight", "-big_bass_weight", "-num_fish_weighed")

    angler = ForeignKey(Angler, null=True, on_delete=DO_NOTHING)
    buy_in = BooleanField(default=False)
    points = IntegerField(default=0)
    day_num = IntegerField(default=1)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)
    total_weight = FloatField(default=0.0)
    place_finish = IntegerField(default=0)
    num_fish_dead = IntegerField(default=0)
    num_fish_alive = IntegerField(default=0)
    big_bass_weight = FloatField(default=0.0)
    penalty_weight = FloatField(default=0.0)
    num_fish_weighed = IntegerField(default=0)
    fish_1_wt = FloatField(default=0.0)
    fish_1_len = FloatField(default=0.0)
    fish_1_alive = BooleanField(default=False)
    fish_2_wt = FloatField(default=0.0)
    fish_2_len = FloatField(default=0.0)
    fish_2_alive = BooleanField(default=False)
    fish_3_wt = FloatField(default=0.0)
    fish_3_len = FloatField(default=0.0)
    fish_3_alive = BooleanField(default=False)
    fish_4_wt = FloatField(default=0.0)
    fish_4_len = FloatField(default=0.0)
    fish_4_alive = BooleanField(default=False)
    fish_5_wt = FloatField(default=0.0)
    fish_5_len = FloatField(default=0.0)
    fish_5_alive = BooleanField(default=False)

    def __str__(self):
        """String representation of a Result object"""
        tourney = "" if self.tournament is None else self.tournament.name
        tw_stats = f"{self.angler.user.get_full_name()} {tourney} | {self.total_weight:.2f}lbs TW"
        bb_stats = f"{self.big_bass_weight:.2f}lbs BB" if not self.buy_in else "Buy-In"
        return f"{tw_stats} | {bb_stats}"

    def get_absolute_url(self):
        """Get url of the result"""
        return reverse("result-add", kwargs={"pk": self.tournament.pk})

    def save(self, *args, **kwargs):
        """Save the result

        Upon save() ... we should do a few things:
        * Calculate the total weight (applying the appropriate penalty)
        * Calculate the number of fish alive (if not entered)
        * Generate the fish weight based on the length if the length is entered
        * Generate the fish length based on the weight if the weight is entered
        """
        self.penalty_weight = self.num_fish_dead * self.tournament.rules.dead_fish_penalty
        # Calculate the number of fish alive
        self.num_fish_alive = self.num_fish_weighed - self.num_fish_dead

        # Generate the fish length based on the weight if the weight is entered
        # Generate the fish weight based on the length if the length is entered
        weighed_fish = [
            self.fish_1_wt,
            self.fish_2_wt,
            self.fish_3_wt,
            self.fish_4_wt,
            self.fish_5_wt,
        ]
        measured_fish = [
            self.fish_1_len,
            self.fish_2_len,
            self.fish_3_len,
            self.fish_4_len,
            self.fish_5_len,
        ]
        if sum(weighed_fish) > 0.0 and sum(measured_fish) == 0.0:  # Weights, not lengths entered
            self.fish_1_len = get_length_from_weight(self.fish_1_wt)
            self.fish_2_len = get_length_from_weight(self.fish_2_wt)
            self.fish_3_len = get_length_from_weight(self.fish_3_wt)
            self.fish_4_len = get_length_from_weight(self.fish_4_wt)
            self.fish_5_len = get_length_from_weight(self.fish_5_wt)
        elif sum(weighed_fish) == 0.0 and sum(measured_fish) > 0.0:  # Lengths, not weights entered
            self.fish_1_wt = get_weight_from_length(self.fish_1_len)
            self.fish_2_wt = get_weight_from_length(self.fish_2_len)
            self.fish_3_wt = get_weight_from_length(self.fish_3_len)
            self.fish_4_wt = get_weight_from_length(self.fish_4_len)
            self.fish_5_wt = get_weight_from_length(self.fish_5_len)

        # Calcualte total weight
        self.total_weight = round(sum(weighed_fish) - self.penalty_weight, 2)
        if self.num_fish_weighed > 0:
            catches = [
                (self.fish_1_wt, self.fish_1_alive),
                (self.fish_2_wt, self.fish_2_alive),
                (self.fish_3_wt, self.fish_3_alive),
                (self.fish_4_wt, self.fish_4_alive),
                (self.fish_5_wt, self.fish_5_alive),
            ]
            eligible_fish = [weight for weight, alive in catches if alive is True]
            self.big_bass_weight = max(eligible_fish) if eligible_fish else 0.0

        super().save(*args, **kwargs)


class MultidayResult(Model):
    """Creates a sum of two results from a multi-day tournament"""

    class Meta:
        """Meta class to ensure ordering of results by the largest:
        total_weight, big_bass_weight, and number of fish_weighed

        This is essentially our tie breaker process implemented with Django query
        """

        ordering = ("-total_weight", "-big_bass_weight", "-num_fish_weighed")

    angler = ForeignKey(Angler, null=True, on_delete=DO_NOTHING)
    tournament = ForeignKey(Tournament, on_delete=DO_NOTHING)

    day_1 = ForeignKey(Result, null=True, related_name="+", on_delete=DO_NOTHING)
    day_2 = ForeignKey(Result, null=True, on_delete=DO_NOTHING)

    buy_in = BooleanField(default=False)
    total_weight = FloatField(default=0.0)
    place_finish = IntegerField(default=0)
    num_fish_dead = IntegerField(default=0)
    num_fish_alive = IntegerField(default=0)
    big_bass_weight = FloatField(default=0.0)
    penalty_weight = FloatField(default=0.0)
    num_fish_weighed = IntegerField(default=0)

    def __str__(self):
        """String representation of a MultidayResult"""
        tourney = "" if self.tournament is None else self.tournament.name
        tw_stats = f"{self.angler.user.get_full_name()} {tourney} | {self.total_weight:.2f}lbs TW"
        bb_stats = f"{self.big_bass_weight:.2f}lbs BB" if not self.buy_in else "Buy-In"
        return f"{tw_stats} | {bb_stats}"

    def save(self, *args, **kwargs):
        """Saves a MultidayResult object

        Args:
            *args (list) A list of arguments
            **kwargs (dict) A dictionary of keyword arguments
        """
        if all([self.day_1.buy_in, self.day_2.buy_in]):
            self.buy_in = True
        if not self.buy_in:
            self.total_weight = round(self.day_1.total_weight + self.day_2.total_weight, 2)
            self.num_fish_dead = self.day_1.num_fish_dead + self.day_2.num_fish_dead
            self.num_fish_alive = self.day_1.num_fish_alive + self.day_2.num_fish_alive
            self.big_bass_weight = max([self.day_1.big_bass_weight, self.day_2.big_bass_weight])
            self.penalty_weight = self.day_1.penalty_weight + self.day_2.penalty_weight
            self.num_fish_weighed = self.day_1.num_fish_weighed + self.day_2.num_fish_weighed

        super().save(*args, **kwargs)


class TeamResult(Model):
    """This model represents a team result in a tournament"""

    boater = ForeignKey(Angler, related_name="+", on_delete=DO_NOTHING)
    result_1 = ForeignKey(Result, null=True, blank=True, on_delete=DO_NOTHING)
    result_2 = ForeignKey(Result, null=True, blank=True, related_name="+", on_delete=DO_NOTHING)
    place_finish = IntegerField(default=0)

    def __str__(self):
        angler_1 = self.result_1.angler.user.get_full_name()
        if self.result_2:
            angler_2 = self.result_2.angler.user.get_full_name()
            return f"Team: {angler_1} & {angler_2}"

        return f"Team: {angler_1} - SOLO"

    def get_absolute_url(self):
        """Returns the absolute url for this model"""
        return reverse("team-details", kwargs={"pk": self.id})
