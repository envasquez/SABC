from core.query_service.base import QueryServiceBase
from core.query_service.event_queries_admin import get_past_admin_query, get_upcoming_admin_query


class EventQueries(QueryServiceBase):
    def get_upcoming_events(self) -> list[dict]:
        return self.fetch_all("""
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
        """)

    def get_past_events(self) -> list[dict]:
        return self.fetch_all("""
            SELECT e.*,
                   t.id as tournament_id,
                   t.complete,
                   t.lake_name,
                   t.ramp_name
            FROM events e
            LEFT JOIN tournaments t ON e.id = t.event_id
            WHERE e.date < CURRENT_DATE
            ORDER BY e.date DESC
        """)

    def get_admin_events_data(
        self,
        upcoming_limit: int = 20,
        upcoming_offset: int = 0,
        past_limit: int = 20,
        past_offset: int = 0,
    ) -> dict:
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
