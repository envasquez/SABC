"""Event-related database queries with full type safety."""

from typing import Any, Dict, List

from core.query_service.base import QueryServiceBase
from core.query_service.event_queries_admin import get_past_admin_query, get_upcoming_admin_query


class EventQueries(QueryServiceBase):
    """Query service for event database operations."""

    def get_upcoming_events(self) -> List[Dict[str, Any]]:
        """
        Get all upcoming events with associated poll and tournament data.

        Returns:
            List of event dictionaries with poll_id, tournament_id, and completion status
        """
        return self.fetch_all(
            """
            SELECT e.*,
                   p.id as poll_id,
                   p.starts_at,
                   p.closes_at,
                   t.id as tournament_id,
                   t.complete as tournament_complete
            FROM events e
            LEFT JOIN polls p ON e.id = p.event_id
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE e.date >= CURRENT_DATE
            ORDER BY e.date
        """
        )

    def get_past_events(self) -> List[Dict[str, Any]]:
        """
        Get all past events with associated tournament data.

        Returns:
            List of event dictionaries with tournament details
        """
        return self.fetch_all(
            """
            SELECT e.*,
                   t.id as tournament_id,
                   t.complete,
                   t.lake_name,
                   t.ramp_name
            FROM events e
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE e.date < CURRENT_DATE
            ORDER BY e.date DESC
        """
        )

    def get_admin_events_data(
        self,
        upcoming_limit: int = 20,
        upcoming_offset: int = 0,
        past_limit: int = 20,
        past_offset: int = 0,
    ) -> Dict[str, Any]:
        """
        Get paginated event data for admin interface.

        Args:
            upcoming_limit: Maximum number of upcoming events to return
            upcoming_offset: Number of upcoming events to skip
            past_limit: Maximum number of past events to return
            past_offset: Number of past events to skip

        Returns:
            Dictionary with total counts and paginated event lists
        """
        total_upcoming = self.fetch_value("SELECT COUNT(*) FROM events WHERE date >= CURRENT_DATE")
        total_past = self.fetch_value(
            "SELECT COUNT(*) FROM events WHERE date < CURRENT_DATE AND event_type != 'holiday'"
        )

        upcoming_events = self.fetch_all(
            get_upcoming_admin_query(),
            {"limit": upcoming_limit, "offset": upcoming_offset},
        )

        past_events = self.fetch_all(
            get_past_admin_query(),
            {"limit": past_limit, "offset": past_offset},
        )

        return {
            "total_upcoming": total_upcoming,
            "total_past": total_past,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
        }
