"""Statistics related queries."""

from typing import Optional

from core.query_service.base import QueryServiceBase


class StatsQueries(QueryServiceBase):
    """Statistics query methods."""

    def get_angler_stats(self, angler_id: int, year: Optional[int] = None) -> dict:
        """Get statistics for an angler."""
        year_filter = "AND EXTRACT(YEAR FROM e.date) = :year" if year else ""
        params = {"angler_id": angler_id}
        if year:
            params["year"] = str(year)

        return self.fetch_one(
            f"""
            SELECT
                COUNT(DISTINCT r.tournament_id) as tournaments_fished,
                SUM(r.num_fish) as total_fish,
                SUM(r.total_weight) as total_weight,
                MAX(r.big_bass_weight) as biggest_bass,
                AVG(r.total_weight) as avg_weight
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            WHERE r.angler_id = :angler_id
            {year_filter}
        """,
            params,
        ) or {
            "tournaments_fished": 0,
            "total_fish": 0,
            "total_weight": 0,
            "biggest_bass": 0,
            "avg_weight": 0,
        }
