"""
Reusable calculation components for tournament functionality.

This module contains calculators that can be used across different parts
of the application for consistent tournament-related calculations.
"""

from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple, Union

from ..models.results import Result


class PointsCalculator:
    """Reusable component for tournament points calculations."""

    @staticmethod
    def calculate_angler_of_year_points(
        results: List[Result], use_place_finish: bool = True
    ) -> int:
        """
        Calculate total points for an angler across multiple tournaments.

        Args:
            results: List of Result objects for an angler
            use_place_finish: Whether to use place_finish for points calculation

        Returns:
            Total points earned by the angler
        """
        total_points = 0
        for result in results:
            if result.points:
                total_points += int(result.points)
            elif use_place_finish and result.place_finish:
                # Fallback calculation based on place finish if points not set
                total_points += max(0, 101 - int(result.place_finish))
        return total_points

    @staticmethod
    def calculate_points_by_placement(
        place_finish: int, total_participants: int
    ) -> int:
        """
        Calculate points based on tournament placement.

        Args:
            place_finish: Final placement in tournament (1st, 2nd, etc.)
            total_participants: Total number of participants

        Returns:
            Points earned for this placement
        """
        if place_finish <= 0:
            return 0
        return max(0, total_participants - place_finish + 1)

    @staticmethod
    def calculate_weighted_points(
        place_finish: int, tournament_multiplier: Decimal = Decimal("1.0")
    ) -> Decimal:
        """
        Calculate weighted points for special tournaments.

        Args:
            place_finish: Final placement in tournament
            tournament_multiplier: Multiplier for special tournaments

        Returns:
            Weighted points for this result
        """
        base_points = max(0, 101 - place_finish) if place_finish > 0 else 0
        return Decimal(str(base_points)) * tournament_multiplier


class RankingCalculator:
    """Reusable component for tournament ranking calculations."""

    @staticmethod
    def calculate_tournament_rankings(results: List[Result]) -> List[Result]:
        """
        Calculate tournament rankings based on weight and fish count.

        Args:
            results: List of Result objects to rank

        Returns:
            List of results sorted by ranking criteria
        """
        # Sort by total weight (descending), then by fish count (descending)
        return sorted(
            results,
            key=lambda r: (
                -float(r.total_weight),
                -int(r.num_fish),
                r.angler.user.last_name,
            ),
        )

    @staticmethod
    def assign_place_finishes(results: List[Result]) -> List[Result]:
        """
        Assign place_finish values to a list of results.

        Args:
            results: List of Result objects to assign places to

        Returns:
            List of results with place_finish assigned
        """
        ranked_results = RankingCalculator.calculate_tournament_rankings(results)

        for index, result in enumerate(ranked_results, start=1):
            result.place_finish = index

        return ranked_results

    @staticmethod
    def calculate_angler_of_year_rankings(
        angler_summaries: List[Dict],
    ) -> List[Dict]:
        """
        Calculate Angler of the Year rankings from summary data.

        Args:
            angler_summaries: List of dictionaries with angler statistics

        Returns:
            List of angler summaries sorted by AOY criteria
        """
        return sorted(
            angler_summaries,
            key=lambda a: (-a.get("total_points", 0), -a.get("total_weight", 0)),
        )


class StatisticsCalculator:
    """Reusable component for tournament statistics calculations."""

    @staticmethod
    def calculate_tournament_statistics(
        results: List[Result],
    ) -> Dict[str, Union[int, float, Result, None]]:
        """
        Calculate comprehensive tournament statistics.

        Args:
            results: List of Result objects for the tournament

        Returns:
            Dictionary containing calculated statistics
        """
        if not results:
            return {}

        # Filter valid results (non-buy-ins, non-DQs)
        valid_results = [r for r in results if not r.buy_in and not r.disqualified]

        if not valid_results:
            return {}

        # Basic counts
        total_participants = len(valid_results)
        limits = sum(1 for r in valid_results if r.num_fish == 5)
        zeros = sum(1 for r in valid_results if r.num_fish == 0)

        # Weight and fish statistics
        total_weight = sum(float(r.total_weight) for r in valid_results)
        total_fish = sum(int(r.num_fish) for r in valid_results)

        # Big bass analysis
        big_bass_results = [
            r for r in valid_results if r.big_bass_weight >= Decimal("5")
        ]
        big_bass_winner = None
        if big_bass_results:
            big_bass_winner = max(big_bass_results, key=lambda r: r.big_bass_weight)

        # Heavy stringer (1st place)
        heavy_stringer = next((r for r in valid_results if r.place_finish == 1), None)

        return {
            "total_participants": total_participants,
            "limits": limits,
            "zeros": zeros,
            "total_fish": total_fish,
            "total_weight": float(total_weight),
            "average_weight": float(total_weight / total_participants)
            if total_participants > 0
            else 0,
            "big_bass_winner": big_bass_winner,
            "big_bass_weight": float(big_bass_winner.big_bass_weight)
            if big_bass_winner
            else 0,
            "heavy_stringer": heavy_stringer,
            "heavy_stringer_weight": float(heavy_stringer.total_weight)
            if heavy_stringer
            else 0,
        }

    @staticmethod
    def calculate_angler_career_stats(
        results: List[Result],
    ) -> Dict[str, Union[int, float, Result, None]]:
        """
        Calculate career statistics for an angler.

        Args:
            results: List of all Result objects for the angler

        Returns:
            Dictionary containing career statistics
        """
        if not results:
            return {}

        valid_results = [r for r in results if not r.buy_in and not r.disqualified]

        if not valid_results:
            return {}

        total_tournaments = len(valid_results)
        total_points = sum(int(r.points or 0) for r in valid_results)
        total_weight = sum(float(r.total_weight) for r in valid_results)
        total_fish = sum(int(r.num_fish) for r in valid_results)

        # Find best finishes
        wins = sum(1 for r in valid_results if r.place_finish == 1)
        top_3s = sum(1 for r in valid_results if r.place_finish <= 3)
        top_5s = sum(1 for r in valid_results if r.place_finish <= 5)

        # Find biggest bass
        biggest_bass = max(valid_results, key=lambda r: r.big_bass_weight, default=None)

        return {
            "total_tournaments": total_tournaments,
            "total_points": total_points,
            "total_weight": float(total_weight),
            "total_fish": total_fish,
            "average_weight_per_tournament": float(total_weight / total_tournaments)
            if total_tournaments > 0
            else 0,
            "wins": wins,
            "top_3_finishes": top_3s,
            "top_5_finishes": top_5s,
            "win_percentage": float(wins / total_tournaments * 100)
            if total_tournaments > 0
            else 0,
            "biggest_bass": biggest_bass,
            "biggest_bass_weight": float(biggest_bass.big_bass_weight)
            if biggest_bass
            else 0,
        }

    @staticmethod
    def calculate_tournament_averages(results: List[Result]) -> Dict[str, float]:
        """
        Calculate tournament averages across multiple tournaments.

        Args:
            results: List of Result objects across tournaments

        Returns:
            Dictionary containing average statistics
        """
        if not results:
            return {}

        valid_results = [r for r in results if not r.buy_in and not r.disqualified]

        if not valid_results:
            return {}

        tournament_count = len(set(r.tournament.id for r in valid_results))

        return {
            "average_weight_per_tournament": float(
                sum(float(r.total_weight) for r in valid_results) / tournament_count
            ),
            "average_fish_per_tournament": float(
                sum(int(r.num_fish) for r in valid_results) / tournament_count
            ),
            "average_participants_per_tournament": float(
                len(valid_results) / tournament_count
            ),
        }
