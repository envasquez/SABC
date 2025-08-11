"""
Reusable validation components for tournament functionality.

This module contains validators that can be used across different parts
of the application for consistent tournament-related validation.
"""

from decimal import Decimal
from typing import List, Optional, Tuple

from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament


class TournamentDataValidator:
    """Reusable component for tournament data validation."""

    @staticmethod
    def validate_result_data(result: Result) -> Tuple[bool, str]:
        """
        Validate tournament result data according to business rules.

        Args:
            result: Result instance to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Basic data validation
        if int(result.num_fish) < 0:
            return False, "Number of fish cannot be negative"

        if float(result.total_weight) < 0:
            return False, "Total weight cannot be negative"

        if float(result.big_bass_weight) < 0:
            return False, "Big bass weight cannot be negative"

        # Business rule validations
        if int(result.num_fish) == 0 and float(result.total_weight) > 0:
            return (
                False,
                f"Cannot have weight: {result.total_weight}lbs with {result.num_fish} fish weighed!",
            )

        # Tournament-specific validations
        if result.tournament and result.tournament.rules:
            if int(result.num_fish) > int(result.tournament.rules.limit_num):
                return (
                    False,
                    f"Number of Fish exceeds limit: {result.tournament.rules.limit_num}",
                )

            # Validate total weight doesn't exceed reasonable limits
            max_total_weight = int(result.tournament.rules.limit_num) * Decimal(
                "15"
            )  # 15lbs per fish max
            if float(result.total_weight) > float(max_total_weight):
                return (
                    False,
                    f"Total weight {result.total_weight}lbs exceeds maximum possible: {max_total_weight}lbs",
                )

        # Big bass validation
        if float(result.big_bass_weight) > float(result.total_weight):
            return (
                False,
                f"Big bass weight {result.big_bass_weight}lbs cannot exceed total weight {result.total_weight}lbs",
            )

        return True, ""

    @staticmethod
    def validate_tournament_completion(
        tournament: Tournament,
    ) -> Tuple[bool, List[str]]:
        """
        Validate that a tournament is ready to be marked as complete.

        Args:
            tournament: Tournament instance to validate

        Returns:
            Tuple of (is_valid, list_of_warnings)
        """
        warnings = []

        # Check if tournament has any results
        results = Result.objects.filter(tournament=tournament)
        if not results.exists():
            warnings.append("Tournament has no results entered")

        # Check for unplaced results
        unplaced_results = results.filter(
            place_finish__isnull=True, buy_in=False, disqualified=False
        )
        if unplaced_results.exists():
            warnings.append(
                f"{unplaced_results.count()} results do not have place assignments"
            )

        # Check for duplicate places
        placed_results = results.filter(
            place_finish__isnull=False, buy_in=False, disqualified=False
        )
        if placed_results.exists():
            places = [r.place_finish for r in placed_results]
            if len(places) != len(set(places)):
                warnings.append("Duplicate place finishes detected")

        # Check place sequence
        if placed_results.exists():
            sorted_places = sorted(places)
            expected_places = list(range(1, len(sorted_places) + 1))
            if sorted_places != expected_places:
                warnings.append(
                    "Place finishes are not sequential (missing places detected)"
                )

        return len(warnings) == 0, warnings

    @staticmethod
    def validate_team_formation(
        tournament: Tournament, result_1: Result, result_2: Optional[Result] = None
    ) -> Tuple[bool, str]:
        """
        Validate team formation for team tournaments.

        Args:
            tournament: Tournament instance
            result_1: Primary team member result
            result_2: Optional secondary team member result

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if results belong to the tournament
        if result_1.tournament != tournament:
            return False, "Result 1 does not belong to this tournament"

        if result_2 and result_2.tournament != tournament:
            return False, "Result 2 does not belong to this tournament"

        # Check for buy-ins or DQs
        if result_1.buy_in:
            return False, "Cannot create team with buy-in result"

        if result_1.disqualified:
            return False, "Cannot create team with disqualified result"

        if result_2:
            if result_2.buy_in:
                return False, "Cannot create team with buy-in result"

            if result_2.disqualified:
                return False, "Cannot create team with disqualified result"

        # Check for existing team memberships
        existing_teams = TeamResult.objects.filter(tournament=tournament)
        used_results = set()

        for team in existing_teams:
            used_results.add(team.result_1.id)
            if team.result_2:
                used_results.add(team.result_2.id)

        if result_1.id in used_results:
            return False, f"Angler {result_1.angler} is already on a team"

        if result_2 and result_2.id in used_results:
            return False, f"Angler {result_2.angler} is already on a team"

        # Check for same angler
        if result_2 and result_1.angler == result_2.angler:
            return False, "Cannot pair an angler with themselves"

        return True, ""

    @staticmethod
    def validate_points_assignment(results: List[Result]) -> Tuple[bool, List[str]]:
        """
        Validate points assignment for tournament results.

        Args:
            results: List of Result objects to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check that all results have place_finish assigned
        for result in results:
            if (
                not result.buy_in
                and not result.disqualified
                and not result.place_finish
            ):
                errors.append(f"Result for {result.angler} missing place finish")

        # Check points assignment logic
        valid_results = [r for r in results if not r.buy_in and not r.disqualified]
        total_participants = len(valid_results)

        for result in valid_results:
            if result.place_finish:
                expected_points = max(
                    0, total_participants - int(result.place_finish) + 1
                )
                if result.points != expected_points:
                    errors.append(
                        f"Points mismatch for {result.angler}: "
                        f"expected {expected_points}, got {result.points}"
                    )

        return len(errors) == 0, errors

    @staticmethod
    def validate_penalty_weights(result: Result) -> Tuple[bool, str]:
        """
        Validate penalty weight assignments.

        Args:
            result: Result instance to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if float(result.penalty_weight) < 0:
            return False, "Penalty weight cannot be negative"

        if float(result.penalty_weight) > float(result.total_weight):
            return (
                False,
                f"Penalty weight {result.penalty_weight}lbs cannot exceed total weight {result.total_weight}lbs",
            )

        return True, ""
