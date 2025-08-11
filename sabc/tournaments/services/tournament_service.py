"""
Tournament-related business logic service.

This module provides centralized business logic for tournament operations,
extracted from views to improve separation of concerns and maintainability.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from ..components.calculators import StatisticsCalculator
from ..components.validators import TournamentDataValidator
from ..models.results import Result, TeamResult
from ..models.tournaments import Tournament, get_payouts


class TournamentService:
    """Service class for tournament business logic operations."""

    @staticmethod
    def calculate_tournament_statistics(
        tournament: Tournament, all_results: List[Result]
    ) -> Dict[str, Union[int, str]]:
        """
        Calculate comprehensive tournament statistics using reusable components.

        Args:
            tournament: Tournament instance
            all_results: List of all Result instances for this tournament

        Returns:
            Dictionary containing tournament statistics
        """
        if not tournament.complete:
            return {}

        # Use reusable statistics calculator component
        stats = StatisticsCalculator.calculate_tournament_statistics(all_results)

        # Format for template display
        formatted_stats = {
            "limits": stats.get("limits", 0),
            "zeros": stats.get("zeros", 0),
            "anglers": stats.get("total_participants", 0),
            "buy_ins": sum(1 for r in all_results if r.buy_in),
            "total_fish": stats.get("total_fish", 0),
            "total_weight": f"{stats.get('total_weight', 0): .2f}lbs",
            "big_bass": (
                f"{stats.get('big_bass_weight', 0): .2f}lbs"
                if float(stats.get("big_bass_weight", 0)) > 0
                else "--"
            ),
            "heavy_stringer": (
                f"{stats.get('heavy_stringer_weight', 0)}lbs"
                if float(stats.get("heavy_stringer_weight", 0)) > 0
                else "--"
            ),
        }

        return formatted_stats

    @staticmethod
    def get_formatted_payouts(tournament_id: int) -> Dict[str, str]:
        """
        Get formatted payout information for a tournament.

        Args:
            tournament_id: Tournament primary key

        Returns:
            Dictionary with payout information formatted as currency strings
        """
        payouts = get_payouts(tid=tournament_id)
        return {key: f"${val:.2f}" for key, val in payouts.items()}

    @staticmethod
    def filter_and_sort_results(
        all_results: List[Result],
    ) -> Tuple[List[Result], List[Result], List[Result]]:
        """
        Filter and sort results into individual, buy-in, and disqualified categories.

        Args:
            all_results: List of all Result instances

        Returns:
            Tuple of (individual_results, buy_in_results, disqualified_results)
        """
        # Filter results efficiently
        indv_results = [r for r in all_results if not r.buy_in and not r.disqualified]
        indv_results.sort(
            key=lambda x: (
                x.place_finish or 999,
                -float(x.total_weight),
                -int(x.num_fish),
            )
        )

        buy_ins = [r for r in all_results if r.buy_in]
        dqs = [r for r in all_results if r.disqualified]

        return indv_results, buy_ins, dqs

    @staticmethod
    def get_optimized_tournament_data(tournament_id: int) -> Tournament:
        """
        Get tournament data with optimized database queries.

        Args:
            tournament_id: Tournament primary key

        Returns:
            Tournament instance with prefetched related data
        """
        return (
            Tournament.objects.select_related(
                "lake", "event", "rules", "payout_multiplier"
            )
            .prefetch_related(
                "result_set__angler__user",
                "teamresult_set__result_1__angler__user",
                "teamresult_set__result_2__angler__user",
            )
            .get(pk=tournament_id)
        )

    @staticmethod
    def get_team_results_data(tournament: Tournament) -> List[TeamResult]:
        """
        Get team results with proper sorting and related data.

        Args:
            tournament: Tournament instance

        Returns:
            List of sorted TeamResult instances
        """
        return list(
            tournament.teamresult_set.select_related(
                "result_1__angler__user", "result_2__angler__user"
            ).order_by("place_finish", "-total_weight", "-num_fish")
        )


class ResultValidationService:
    """Service class for result validation business logic."""

    @staticmethod
    def validate_result(result: Result, is_new_result: bool = True) -> Tuple[bool, str]:
        """
        Validate a tournament result using reusable validation components.

        Args:
            result: Result instance to validate
            is_new_result: Whether this is a new result or an update

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for duplicate result if new
        if is_new_result:
            existing_results = Result.objects.filter(
                tournament=result.tournament.id, angler=result.angler
            )
            if existing_results.exists():
                return (
                    False,
                    f"ERROR Result exists for {result.angler} ... edit instead?",
                )

        # Use reusable validator component
        is_valid, error_message = TournamentDataValidator.validate_result_data(result)
        if not is_valid:
            return False, f"ERROR {error_message}"

        return True, ""


class TeamResultService:
    """Service class for team result business logic."""

    @staticmethod
    def get_available_results_for_teams(tournament_id: int) -> List[Result]:
        """
        Get results that are available for team formation.

        Args:
            tournament_id: Tournament primary key

        Returns:
            List of Result instances not already used in teams
        """
        all_results = list(
            Result.objects.filter(tournament=tournament_id, buy_in=False)
        )
        team_results = list(TeamResult.objects.filter(tournament=tournament_id))

        used_result_ids = set()
        for team_result in team_results:
            used_result_ids.add(team_result.result_1.id)
            if team_result.result_2:
                used_result_ids.add(team_result.result_2.id)

        return [r for r in all_results if r.id not in used_result_ids]

    @staticmethod
    def validate_team_formation(
        tournament_id: int, result_1: Result, result_2: Optional[Result] = None
    ) -> Tuple[bool, str]:
        """
        Validate team result formation using reusable validation components.

        Args:
            tournament_id: Tournament primary key
            result_1: Primary team member result
            result_2: Optional secondary team member result

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Get tournament instance
        tournament = Tournament.objects.get(pk=tournament_id)

        # Use reusable validator component
        is_valid, error_message = TournamentDataValidator.validate_team_formation(
            tournament, result_1, result_2
        )

        return is_valid, error_message

    @staticmethod
    def format_team_message(result_1: Result, result_2: Optional[Result] = None) -> str:
        """
        Format success message for team creation.

        Args:
            result_1: Primary team member result
            result_2: Optional secondary team member result

        Returns:
            Formatted success message
        """
        msg = f"{result_1.angler}"
        if result_2:
            msg += f" & {result_2.angler}"
        else:
            msg += " - solo"
        return f"Team added: {msg}"
