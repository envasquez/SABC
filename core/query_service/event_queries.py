"""Event-related database queries with full type safety."""

from typing import Any, Dict, List

from core.query_service.base import QueryServiceBase

# Admin-events queries kept inline because their only callers are
# `get_admin_events_data` below.
_UPCOMING_ADMIN_QUERY = """
    SELECT e.id, e.date, e.name, e.description, e.event_type,
           EXTRACT(DOW FROM e.date) as day_num,
           CASE EXTRACT(DOW FROM e.date)
               WHEN 0 THEN 'Sunday' WHEN 1 THEN 'Monday' WHEN 2 THEN 'Tuesday'
               WHEN 3 THEN 'Wednesday' WHEN 4 THEN 'Thursday' WHEN 5 THEN 'Friday'
               WHEN 6 THEN 'Saturday'
           END as day_name,
           EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
           EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
           EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id
               AND CURRENT_TIMESTAMP BETWEEN p.starts_at AND p.closes_at) as poll_active,
           e.start_time, e.weigh_in_time, e.entry_fee, e.lake_name,
           e.ramp_name, e.holiday_name,
           EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id
               AND t.complete = true) as tournament_complete
    FROM events e
    WHERE e.date >= CURRENT_DATE
    ORDER BY e.date
    LIMIT :limit OFFSET :offset
"""

_PAST_ADMIN_QUERY = """
    SELECT e.id, e.date, e.name, e.description, e.event_type, e.entry_fee,
           e.lake_name, e.start_time, e.weigh_in_time, e.holiday_name,
           EXISTS(SELECT 1 FROM polls p WHERE p.event_id = e.id) as has_poll,
           EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id) as has_tournament,
           EXISTS(SELECT 1 FROM tournaments t WHERE t.event_id = e.id
               AND t.complete = true) as tournament_complete,
           EXISTS(SELECT 1 FROM tournaments t JOIN results r ON t.id = r.tournament_id
               WHERE t.event_id = e.id) as has_results
    FROM events e
    WHERE e.date < CURRENT_DATE AND event_type != 'holiday'
    ORDER BY e.date DESC
    LIMIT :limit OFFSET :offset
"""


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
            _UPCOMING_ADMIN_QUERY,
            {"limit": upcoming_limit, "offset": upcoming_offset},
        )

        past_events = self.fetch_all(
            _PAST_ADMIN_QUERY,
            {"limit": past_limit, "offset": past_offset},
        )

        return {
            "total_upcoming": total_upcoming,
            "total_past": total_past,
            "upcoming_events": upcoming_events,
            "past_events": past_events,
        }
