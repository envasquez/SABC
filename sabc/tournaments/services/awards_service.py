"""
Annual awards business logic service.

This module provides centralized business logic for annual award calculations,
extracted from views to improve separation of concerns and maintainability.
"""

import datetime
from decimal import Decimal
from typing import Dict, List, Optional

from django.core.cache import cache
from django.db.models import Count, Max, Q, Sum
from users.models import Angler

from ..models.results import Result


class AnnualAwardsService:
    """Service class for annual awards business logic operations."""

    @staticmethod
    def get_angler_of_year_results(year: Optional[int] = None) -> List[Dict]:
        """
        Calculate Angler of the Year standings using optimized database queries.

        Args:
            year: Year to calculate standings for, defaults to current year

        Returns:
            List of dictionaries containing angler standings data
        """
        if year is None:
            year = datetime.date.today().year

        # Check cache first
        cache_key = f"aoy_results_{year}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Get all results for the year with related data
        all_results = Result.objects.filter(
            tournament__event__year=year,
            angler__user__is_active=True,
            angler__member=True,
            tournament__complete=True,
            tournament__points_count=True,
        ).select_related("angler__user", "tournament__event")

        # Use dictionary to aggregate by angler efficiently
        angler_stats = {}
        for result in all_results:
            angler_key = result.angler.pk
            if angler_key not in angler_stats:
                angler_stats[angler_key] = {
                    "angler": result.angler.user.get_full_name(),
                    "angler_id": angler_key,
                    "total_points": 0,
                    "total_weight": 0.0,
                    "total_fish": 0,
                    "events": 0,
                }

            angler_stats[angler_key]["total_points"] += result.points or 0
            angler_stats[angler_key]["total_weight"] += float(result.total_weight or 0)
            angler_stats[angler_key]["total_fish"] += result.num_fish or 0
            angler_stats[angler_key]["events"] += 1

        # Convert to list and sort
        formatted_results = list(angler_stats.values())
        formatted_results.sort(key=lambda x: (-x["total_points"], -x["total_weight"]))

        # Cache the results for performance
        cache.set(cache_key, formatted_results, timeout=600)  # Cache for 10 minutes
        return formatted_results

    @staticmethod
    def get_heavy_stringer_winner(year: Optional[int] = None) -> List[Dict]:
        """
        Get the heavy stringer (heaviest total weight) winner for the year.

        Args:
            year: Year to find winner for, defaults to current year

        Returns:
            List containing winner data (empty if no results)
        """
        if year is None:
            year = datetime.date.today().year

        # Use select_related to avoid additional queries
        result = (
            Result.objects.select_related(
                "angler__user", "tournament__lake", "tournament__event"
            )
            .filter(
                tournament__event__year=year,
                angler__member=True,
                angler__user__is_active=True,
                total_weight__gt=Decimal("0"),
                tournament__complete=True,
            )
            .order_by("-total_weight")
            .first()
        )

        if result:
            return [
                {
                    "angler": result.angler,
                    "weight": result.total_weight,
                    "fish": result.num_fish,
                    "tournament": result.tournament,
                }
            ]
        return []

    @staticmethod
    def get_big_bass_winner(year: Optional[int] = None) -> List[Dict]:
        """
        Get the big bass (heaviest individual fish) winner for the year.

        Args:
            year: Year to find winner for, defaults to current year

        Returns:
            List containing winner data (empty if no results)
        """
        if year is None:
            year = datetime.date.today().year

        # Use select_related to avoid additional queries
        result = (
            Result.objects.select_related(
                "angler__user", "tournament__lake", "tournament__event"
            )
            .filter(
                tournament__event__year=year,
                angler__user__is_active=True,
                big_bass_weight__gte=Decimal("5.0"),
                tournament__complete=True,
            )
            .order_by("-big_bass_weight")
            .first()
        )

        if result:
            return [
                {
                    "angler": result.angler,
                    "weight": result.big_bass_weight,
                    "tournament": result.tournament,
                }
            ]
        return []

    @staticmethod
    def get_yearly_statistics(year: Optional[int] = None) -> Dict:
        """
        Calculate comprehensive yearly tournament statistics.

        Args:
            year: Year to calculate for, defaults to current year

        Returns:
            Dictionary containing yearly statistics
        """
        if year is None:
            year = datetime.date.today().year

        # Check cache first
        cache_key = f"yearly_stats_{year}"
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            return cached_result

        # Get aggregated statistics for the year
        stats = Result.objects.filter(
            tournament__event__year=year, tournament__complete=True
        ).aggregate(
            total_tournaments=Count("tournament", distinct=True),
            total_participants=Count("angler", distinct=True),
            total_fish_caught=Sum("num_fish"),
            total_weight=Sum("total_weight"),
            average_weight_per_angler=Sum("total_weight")
            / Count("angler", distinct=True),
            limits_caught=Count("id", filter=Q(num_fish=5)),
            zeros=Count("id", filter=Q(num_fish=0, buy_in=False)),
        )

        # Calculate additional derived statistics
        if stats["total_fish_caught"] and stats["total_participants"]:
            stats["average_fish_per_angler"] = (
                stats["total_fish_caught"] / stats["total_participants"]
            )
        else:
            stats["average_fish_per_angler"] = 0

        # Cache the results
        cache.set(cache_key, stats, timeout=3600)  # Cache for 1 hour
        return stats


class RosterService:
    """Service class for roster-related business logic."""

    @staticmethod
    def get_optimized_roster_data(
        member_type: str = "all", year: Optional[int] = None
    ) -> List[Angler]:
        """
        Get roster data with statistics optimized for performance.

        Args:
            member_type: Filter by 'members', 'guests', or 'all'
            year: Year for statistics calculation, defaults to current year

        Returns:
            QuerySet of Angler objects with annotated statistics
        """
        if year is None:
            year = datetime.date.today().year

        # Annotate with current year statistics in a single query
        queryset = (
            Angler.objects.select_related("user")
            .annotate(
                total_points=Sum(
                    "result__points",
                    filter=Q(result__tournament__event__year=year),
                ),
                total_events=Count(
                    "result__tournament",
                    filter=Q(result__tournament__event__year=year),
                    distinct=True,
                ),
                total_weight=Sum(
                    "result__total_weight",
                    filter=Q(result__tournament__event__year=year),
                ),
                total_fish=Sum(
                    "result__num_fish",
                    filter=Q(result__tournament__event__year=year),
                ),
            )
            .order_by("user__last_name", "user__first_name")
        )

        # Apply member type filter
        if member_type == "members":
            queryset = queryset.filter(member=True)
        elif member_type == "guests":
            queryset = queryset.filter(member=False)

        return queryset
