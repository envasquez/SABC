"""
Event and calendar business logic service.

This module provides centralized business logic for event and calendar operations,
extracted from views to improve separation of concerns and maintainability.
"""

import datetime
from typing import List, Optional, Tuple

from django.db.models import Q

from ..models.tournaments import Tournament


class EventService:
    """Service class for event-related business logic operations."""

    @staticmethod
    def get_optimized_calendar_events(year: int) -> Tuple[List[Tournament], List]:
        """
        Get calendar events and tournaments with minimal database queries.

        Args:
            year: Year to retrieve events for

        Returns:
            Tuple of (tournaments, calendar_events)
        """
        # Single optimized query for tournaments with related data
        tournaments = (
            Tournament.objects.select_related("lake", "event")
            .filter(event__year=year)
            .only(
                "id",
                "name",
                "complete",
                "lake__name",
                "event__date",
                "event__start",
                "event__finish",
            )
        )

        # Single query for calendar events
        try:
            from ..models.calendar_events import CalendarEvent

            calendar_events = CalendarEvent.objects.filter(date__year=year).only(
                "date", "title", "description", "category"
            )
        except ImportError:
            calendar_events = []

        return list(tournaments), list(calendar_events)

    @staticmethod
    def get_upcoming_events(
        limit: int = 5,
    ) -> Tuple[Optional[Tournament], Optional[Tournament]]:
        """
        Get next upcoming tournament and meeting events.

        Args:
            limit: Maximum number of events to consider

        Returns:
            Tuple of (next_tournament, next_meeting) or (None, None)
        """
        today = datetime.date.today()

        # Get next tournament
        next_tournament = (
            Tournament.objects.select_related("event", "lake")
            .filter(event__date__gte=today)
            .order_by("event__date")
            .first()
        )

        # For meetings, we would need to check Events model
        # This is a simplified implementation
        next_meeting = None

        return next_tournament, next_meeting

    @staticmethod
    def get_events_by_date_range(
        start_date: datetime.date, end_date: datetime.date
    ) -> List[Tournament]:
        """
        Get tournaments within a specific date range.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            List of Tournament objects within the date range
        """
        return (
            Tournament.objects.select_related("lake", "event")
            .filter(event__date__gte=start_date, event__date__lte=end_date)
            .order_by("event__date")
        )

    @staticmethod
    def get_current_year_tournaments() -> List[Tournament]:
        """
        Get all tournaments for the current year with optimized queries.

        Returns:
            List of Tournament objects for current year
        """
        current_year = datetime.date.today().year

        return (
            Tournament.objects.select_related("lake", "event", "rules")
            .filter(event__year=current_year)
            .order_by("event__date")
        )

    @staticmethod
    def is_tournament_upcoming(tournament: Tournament) -> bool:
        """
        Check if a tournament is scheduled for the future.

        Args:
            tournament: Tournament instance to check

        Returns:
            True if tournament is upcoming, False otherwise
        """
        return tournament.event.date > datetime.date.today()

    @staticmethod
    def get_completed_tournaments(year: int = None) -> List[Tournament]:
        """
        Get completed tournaments for a specific year.

        Args:
            year: Year to filter by, defaults to current year

        Returns:
            List of completed Tournament objects
        """
        if year is None:
            year = datetime.date.today().year

        return (
            Tournament.objects.select_related("lake", "event")
            .filter(event__year=year, complete=True)
            .order_by("event__date")
        )
