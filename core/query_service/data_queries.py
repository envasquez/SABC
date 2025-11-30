"""Query service for data dashboard statistics and analytics."""

from decimal import Decimal
from typing import Any, Dict, List, Union

from core.query_service.base import QueryServiceBase


def _convert_decimals(value: Any) -> Any:
    """Convert Decimal values to float for JSON serialization."""
    if isinstance(value, Decimal):
        return float(value)
    return value


def _convert_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Convert all Decimal values in a row to float."""
    return {key: _convert_decimals(val) for key, val in row.items()}


class DataQueries(QueryServiceBase):
    """Queries for the data dashboard page."""

    def _fetch_all_converted(self, query: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch all results with Decimal values converted to float."""
        return [_convert_row(row) for row in self.fetch_all(query, params)]

    def _fetch_one_converted(
        self, query: str, params: Dict[str, Any]
    ) -> Union[Dict[str, Any], None]:
        """Fetch one result with Decimal values converted to float."""
        result = self.fetch_one(query, params)
        return _convert_row(result) if result else None

    def get_available_years(self) -> List[int]:
        """Get all years that have tournament data."""
        query = """
            SELECT DISTINCT e.year
            FROM events e
            JOIN tournaments t ON t.event_id = e.id
            WHERE t.complete = true
            ORDER BY e.year DESC
        """
        results = self.fetch_all(query, {})
        return [row["year"] for row in results]

    def get_club_overview_stats(self) -> Dict[str, Any]:
        """Get high-level club statistics across all time."""
        query = """
            SELECT
                COUNT(DISTINCT t.id) as total_tournaments,
                COUNT(DISTINCT r.angler_id) as unique_anglers,
                COALESCE(SUM(r.num_fish), 0) as total_fish,
                COALESCE(SUM(r.total_weight), 0) as total_weight,
                (SELECT COUNT(*) FROM anglers WHERE member = true) as current_members,
                MIN(e.year) as first_year,
                MAX(e.year) as last_year
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
        """
        return self._fetch_one_converted(query, {}) or {
            "total_tournaments": 0,
            "unique_anglers": 0,
            "total_fish": 0,
            "total_weight": 0.0,
            "current_members": 0,
            "first_year": None,
            "last_year": None,
        }

    def get_tournaments_by_year(self) -> List[Dict[str, Any]]:
        """Get tournament counts and stats per year."""
        query = """
            SELECT
                e.year,
                COUNT(DISTINCT t.id) as tournament_count,
                COUNT(DISTINCT r.angler_id) as unique_anglers,
                COALESCE(SUM(r.num_fish), 0) as total_fish,
                COALESCE(SUM(r.total_weight), 0) as total_weight,
                CASE
                    WHEN COUNT(r.id) > 0
                    THEN COALESCE(SUM(r.total_weight), 0) / COUNT(r.id)
                    ELSE 0
                END as avg_weight_per_angler
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY e.year
            ORDER BY e.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_participation_trends(self) -> List[Dict[str, Any]]:
        """Get average participation per tournament by year."""
        query = """
            SELECT
                e.year,
                COUNT(DISTINCT t.id) as tournament_count,
                COUNT(r.id) as total_entries,
                CASE
                    WHEN COUNT(DISTINCT t.id) > 0
                    THEN CAST(COUNT(r.id) AS FLOAT) / COUNT(DISTINCT t.id)
                    ELSE 0
                END as avg_participants
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY e.year
            ORDER BY e.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_lake_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for each lake fished."""
        query = """
            SELECT
                l.id as lake_id,
                l.display_name as lake_name,
                COUNT(DISTINCT t.id) as times_fished,
                MAX(e.date) as last_fished,
                COALESCE(SUM(r.total_weight), 0) as total_weight,
                CASE
                    WHEN COUNT(r.id) > 0
                    THEN COALESCE(SUM(r.total_weight), 0) / COUNT(r.id)
                    ELSE 0
                END as avg_weight_per_angler,
                SUM(CASE WHEN r.num_fish = t.fish_limit THEN 1 ELSE 0 END) as total_limits,
                SUM(CASE WHEN r.num_fish = 0 AND r.disqualified = false THEN 1 ELSE 0 END) as total_zeros,
                MAX(r.big_bass_weight) as biggest_bass
            FROM lakes l
            JOIN tournaments t ON t.lake_id = l.id
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY l.id, l.display_name
            ORDER BY times_fished DESC, lake_name ASC
        """
        return self._fetch_all_converted(query, {})

    def get_lake_usage_by_year(self) -> List[Dict[str, Any]]:
        """Get lake usage breakdown by year for stacked chart."""
        query = """
            SELECT
                e.year,
                l.display_name as lake_name,
                COUNT(DISTINCT t.id) as tournament_count
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            JOIN lakes l ON t.lake_id = l.id
            WHERE t.complete = true
            GROUP BY e.year, l.id, l.display_name
            ORDER BY e.year ASC, tournament_count DESC
        """
        return self._fetch_all_converted(query, {})

    def get_catch_distribution(self) -> List[Dict[str, Any]]:
        """Get distribution of fish counts (0 fish, 1 fish, 2 fish, etc.)."""
        query = """
            SELECT
                r.num_fish as fish_count,
                COUNT(*) as angler_count
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            WHERE t.complete = true AND r.disqualified = false
            GROUP BY r.num_fish
            ORDER BY r.num_fish ASC
        """
        return self._fetch_all_converted(query, {})

    def get_limits_zeros_by_year(self) -> List[Dict[str, Any]]:
        """Get limits and zeros counts per year."""
        query = """
            SELECT
                e.year,
                COUNT(r.id) as total_entries,
                SUM(CASE WHEN r.num_fish = t.fish_limit THEN 1 ELSE 0 END) as limits,
                SUM(CASE WHEN r.num_fish = 0 AND r.disqualified = false THEN 1 ELSE 0 END) as zeros
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY e.year
            ORDER BY e.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_big_bass_records(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top big bass catches of all time."""
        query = """
            SELECT
                a.name as angler_name,
                r.big_bass_weight,
                l.display_name as lake_name,
                e.date as tournament_date,
                e.year
            FROM results r
            JOIN tournaments t ON r.tournament_id = t.id
            JOIN events e ON t.event_id = e.id
            JOIN lakes l ON t.lake_id = l.id
            JOIN anglers a ON r.angler_id = a.id
            WHERE t.complete = true
                AND r.big_bass_weight IS NOT NULL
                AND r.big_bass_weight > 0
            ORDER BY r.big_bass_weight DESC
            LIMIT :limit
        """
        return self._fetch_all_converted(query, {"limit": limit})

    def get_membership_by_year(self) -> List[Dict[str, Any]]:
        """Get member count estimates by year based on tournament participation."""
        # This query counts unique anglers who fished as members each year
        query = """
            SELECT
                e.year,
                COUNT(DISTINCT CASE WHEN r.was_member = true THEN r.angler_id END) as member_count,
                COUNT(DISTINCT CASE WHEN r.was_member = false THEN r.angler_id END) as guest_count,
                COUNT(DISTINCT r.angler_id) as total_anglers
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY e.year
            ORDER BY e.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_weight_trends_by_year(self) -> List[Dict[str, Any]]:
        """Get average weights per tournament by year."""
        query = """
            SELECT
                e.year,
                CASE
                    WHEN COUNT(r.id) > 0
                    THEN COALESCE(SUM(r.total_weight), 0) / COUNT(r.id)
                    ELSE 0
                END as avg_individual_weight,
                CASE
                    WHEN COUNT(DISTINCT t.id) > 0
                    THEN COALESCE(SUM(r.total_weight), 0) / COUNT(DISTINCT t.id)
                    ELSE 0
                END as avg_tournament_total_weight,
                MAX(r.total_weight) as max_individual_weight
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            LEFT JOIN results r ON r.tournament_id = t.id
            WHERE t.complete = true
            GROUP BY e.year
            ORDER BY e.year ASC
        """
        return self._fetch_all_converted(query, {})
