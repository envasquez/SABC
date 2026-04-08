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
        # Combines both individual results and team_results for complete stats
        query = """
            WITH all_results AS (
                -- Individual format results
                SELECT t.id as tournament_id, r.angler_id, r.num_fish, r.total_weight
                FROM tournaments t
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler1)
                SELECT t.id as tournament_id, tr.angler1_id as angler_id, tr.num_fish, tr.total_weight
                FROM tournaments t
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler2, when present)
                SELECT t.id as tournament_id, tr.angler2_id as angler_id, 0 as num_fish, 0 as total_weight
                FROM tournaments t
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true AND tr.angler2_id IS NOT NULL
            )
            SELECT
                (SELECT COUNT(DISTINCT t.id) FROM tournaments t WHERE t.complete = true) as total_tournaments,
                COUNT(DISTINCT ar.angler_id) as unique_anglers,
                COALESCE(SUM(ar.num_fish), 0) as total_fish,
                COALESCE(SUM(ar.total_weight), 0) as total_weight,
                (SELECT COUNT(*) FROM anglers WHERE member = true) as current_members,
                (SELECT MIN(e.year) FROM events e JOIN tournaments t ON t.event_id = e.id WHERE t.complete = true) as first_year,
                (SELECT MAX(e.year) FROM events e JOIN tournaments t ON t.event_id = e.id WHERE t.complete = true) as last_year
            FROM all_results ar
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

    def get_year_comparison_stats(self) -> Dict[str, Any]:
        """Get YTD stats comparing same months across years.

        Compares current year's stats (through current month) against the same
        period in previous years. For example, if it's March, compare Jan-Mar
        of current year against Jan-Mar of all previous years.
        """
        # Combines both individual results and team_results
        query = """
            WITH current_period AS (
                -- Get the latest tournament month in the most recent year
                SELECT
                    MAX(e.year) as current_year,
                    MAX(EXTRACT(MONTH FROM e.date)) as current_month
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                WHERE t.complete = true
                    AND e.year = (SELECT MAX(e2.year) FROM events e2
                                  JOIN tournaments t2 ON t2.event_id = e2.id
                                  WHERE t2.complete = true)
            ),
            all_results AS (
                -- Individual format results
                SELECT t.id as tournament_id, e.year, e.date, r.angler_id, r.num_fish, r.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler1)
                SELECT t.id as tournament_id, e.year, e.date, tr.angler1_id as angler_id, tr.num_fish, tr.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler2, when present) - count as participant but no fish/weight
                SELECT t.id as tournament_id, e.year, e.date, tr.angler2_id as angler_id, 0 as num_fish, 0 as total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true AND tr.angler2_id IS NOT NULL
            ),
            ytd_stats AS (
                -- Calculate YTD stats for each year (same month range)
                SELECT
                    ar.year,
                    COUNT(DISTINCT ar.angler_id) as unique_anglers,
                    COALESCE(SUM(ar.num_fish), 0) as total_fish,
                    COALESCE(SUM(ar.total_weight), 0) as total_weight,
                    CASE
                        WHEN COUNT(*) > 0
                        THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(*)
                        ELSE 0
                    END as avg_weight_per_angler
                FROM all_results ar
                CROSS JOIN current_period cp
                WHERE EXTRACT(MONTH FROM ar.date) <= cp.current_month
                GROUP BY ar.year
                ORDER BY ar.year DESC
            )
            SELECT
                (SELECT unique_anglers FROM ytd_stats ORDER BY year DESC LIMIT 1) as current_anglers,
                (SELECT unique_anglers FROM ytd_stats ORDER BY year DESC LIMIT 1 OFFSET 1) as prev_anglers,
                (SELECT total_fish FROM ytd_stats ORDER BY year DESC LIMIT 1) as current_fish,
                (SELECT total_fish FROM ytd_stats ORDER BY year DESC LIMIT 1 OFFSET 1) as prev_fish,
                (SELECT total_weight FROM ytd_stats ORDER BY year DESC LIMIT 1) as current_weight,
                (SELECT total_weight FROM ytd_stats ORDER BY year DESC LIMIT 1 OFFSET 1) as prev_weight,
                (SELECT avg_weight_per_angler FROM ytd_stats ORDER BY year DESC LIMIT 1) as current_avg_weight,
                (SELECT avg_weight_per_angler FROM ytd_stats ORDER BY year DESC LIMIT 1 OFFSET 1) as prev_avg_weight,
                (SELECT year FROM ytd_stats ORDER BY year DESC LIMIT 1) as current_year,
                (SELECT year FROM ytd_stats ORDER BY year DESC LIMIT 1 OFFSET 1) as prev_year,
                (SELECT current_month FROM current_period) as through_month
        """
        return self._fetch_one_converted(query, {}) or {
            "current_anglers": 0,
            "prev_anglers": 0,
            "current_fish": 0,
            "prev_fish": 0,
            "current_weight": 0.0,
            "prev_weight": 0.0,
            "current_avg_weight": 0.0,
            "prev_avg_weight": 0.0,
            "current_year": None,
            "prev_year": None,
            "through_month": None,
        }

    def get_ytd_trends_by_year(self) -> List[Dict[str, Any]]:
        """Get YTD stats for each year (same month range as current year).

        Returns historical YTD data for sparkline charts, comparing each year's
        performance through the same months as the current year's latest data.
        """
        # Combines both individual results and team_results
        query = """
            WITH current_period AS (
                SELECT
                    MAX(e.year) as current_year,
                    MAX(EXTRACT(MONTH FROM e.date)) as current_month
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                WHERE t.complete = true
                    AND e.year = (SELECT MAX(e2.year) FROM events e2
                                  JOIN tournaments t2 ON t2.event_id = e2.id
                                  WHERE t2.complete = true)
            ),
            all_results AS (
                -- Individual format results
                SELECT e.year, e.date, r.angler_id, r.num_fish, r.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler1)
                SELECT e.year, e.date, tr.angler1_id as angler_id, tr.num_fish, tr.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler2, when present)
                SELECT e.year, e.date, tr.angler2_id as angler_id, 0 as num_fish, 0 as total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true AND tr.angler2_id IS NOT NULL
            )
            SELECT
                ar.year,
                COUNT(DISTINCT ar.angler_id) as unique_anglers,
                COALESCE(SUM(ar.num_fish), 0) as total_fish,
                COALESCE(SUM(ar.total_weight), 0) as total_weight,
                CASE
                    WHEN COUNT(*) > 0
                    THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(*)
                    ELSE 0
                END as avg_weight_per_angler
            FROM all_results ar
            CROSS JOIN current_period cp
            WHERE EXTRACT(MONTH FROM ar.date) <= cp.current_month
            GROUP BY ar.year
            ORDER BY ar.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_tournaments_by_year(self) -> List[Dict[str, Any]]:
        """Get tournament counts and stats per year."""
        # Combines both individual results and team_results
        query = """
            WITH all_results AS (
                -- Individual format results
                SELECT t.id as tournament_id, e.year, r.angler_id, r.num_fish, r.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler1)
                SELECT t.id as tournament_id, e.year, tr.angler1_id as angler_id, tr.num_fish, tr.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler2, when present)
                SELECT t.id as tournament_id, e.year, tr.angler2_id as angler_id, 0 as num_fish, 0 as total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true AND tr.angler2_id IS NOT NULL
            )
            SELECT
                ar.year,
                COUNT(DISTINCT ar.tournament_id) as tournament_count,
                COUNT(DISTINCT ar.angler_id) as unique_anglers,
                COALESCE(SUM(ar.num_fish), 0) as total_fish,
                COALESCE(SUM(ar.total_weight), 0) as total_weight,
                CASE
                    WHEN COUNT(*) > 0
                    THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(*)
                    ELSE 0
                END as avg_weight_per_angler
            FROM all_results ar
            GROUP BY ar.year
            ORDER BY ar.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_participation_trends(self) -> List[Dict[str, Any]]:
        """Get average participation per tournament by year."""
        # Uses individual results as primary source
        # Falls back to team_results only for tournaments without results data
        query = """
            WITH all_participants AS (
                -- Individual results (primary source)
                SELECT t.id as tournament_id, e.year, r.angler_id
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team results angler1 (only for tournaments without individual data)
                SELECT t.id as tournament_id, e.year, tr.angler1_id as angler_id
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
                UNION ALL
                -- Team results angler2 (only for tournaments without individual data)
                SELECT t.id as tournament_id, e.year, tr.angler2_id as angler_id
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                  AND tr.angler2_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
            )
            SELECT
                ap.year,
                COUNT(DISTINCT ap.tournament_id) as tournament_count,
                COUNT(DISTINCT (ap.tournament_id, ap.angler_id)) as total_entries,
                CASE
                    WHEN COUNT(DISTINCT ap.tournament_id) > 0
                    THEN CAST(COUNT(DISTINCT (ap.tournament_id, ap.angler_id)) AS FLOAT) / COUNT(DISTINCT ap.tournament_id)
                    ELSE 0
                END as avg_participants
            FROM all_participants ap
            GROUP BY ap.year
            ORDER BY ap.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_lake_statistics(self) -> List[Dict[str, Any]]:
        """Get statistics for each lake fished."""
        # Combines both individual results and team_results
        query = """
            WITH all_results AS (
                -- Individual format results
                SELECT l.id as lake_id, l.display_name as lake_name, t.id as tournament_id,
                       e.date, r.total_weight, r.num_fish, t.fish_limit,
                       r.disqualified, r.big_bass_weight
                FROM lakes l
                JOIN tournaments t ON t.lake_id = l.id
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (count per boat, not per angler)
                SELECT l.id as lake_id, l.display_name as lake_name, t.id as tournament_id,
                       e.date, tr.total_weight, tr.num_fish, t.fish_limit,
                       false as disqualified, tr.big_bass_weight
                FROM lakes l
                JOIN tournaments t ON t.lake_id = l.id
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
            )
            SELECT
                ar.lake_id,
                ar.lake_name,
                COUNT(DISTINCT ar.tournament_id) as times_fished,
                MAX(ar.date) as last_fished,
                COALESCE(SUM(ar.total_weight), 0) as total_weight,
                CASE
                    WHEN COUNT(*) > 0
                    THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(*)
                    ELSE 0
                END as avg_weight_per_angler,
                SUM(CASE WHEN ar.num_fish = ar.fish_limit THEN 1 ELSE 0 END) as total_limits,
                SUM(CASE WHEN ar.num_fish = 0 AND ar.disqualified = false THEN 1 ELSE 0 END) as total_zeros,
                MAX(ar.big_bass_weight) as biggest_bass
            FROM all_results ar
            GROUP BY ar.lake_id, ar.lake_name
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
        # Uses individual results for accurate per-angler fish counts
        # Falls back to team_results only for tournaments without results data
        query = """
            WITH all_catches AS (
                -- Individual results (primary source)
                SELECT r.num_fish
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                WHERE t.complete = true AND r.disqualified = false
                UNION ALL
                -- Team results only for tournaments without individual data
                -- In this case, split team fish count between anglers
                SELECT COALESCE(tr.num_fish / 2, 0) as num_fish
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                WHERE t.complete = true
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
                UNION ALL
                -- Second angler from team (when present) for tournaments without individual data
                SELECT COALESCE(tr.num_fish / 2, 0) as num_fish
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                WHERE t.complete = true
                  AND tr.angler2_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
            )
            SELECT
                ac.num_fish as fish_count,
                COUNT(*) as angler_count
            FROM all_catches ac
            GROUP BY ac.num_fish
            ORDER BY ac.num_fish ASC
        """
        return self._fetch_all_converted(query, {})

    def get_limits_zeros_by_year(self) -> List[Dict[str, Any]]:
        """Get limits and zeros counts per year."""
        # Uses individual results for accurate per-angler stats
        # Falls back to team_results only for tournaments without results data
        query = """
            WITH all_results AS (
                -- Individual results (primary source)
                SELECT e.year, r.num_fish, t.fish_limit, r.disqualified
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team results only for tournaments without individual data
                SELECT e.year, tr.num_fish, t.fish_limit, false as disqualified
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
            )
            SELECT
                ar.year,
                COUNT(*) as total_entries,
                SUM(CASE WHEN ar.num_fish >= ar.fish_limit THEN 1 ELSE 0 END) as limits,
                SUM(CASE WHEN ar.num_fish = 0 AND ar.disqualified = false THEN 1 ELSE 0 END) as zeros
            FROM all_results ar
            GROUP BY ar.year
            ORDER BY ar.year ASC
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
        # Combines both individual results and team_results
        query = """
            WITH all_participants AS (
                -- Individual format results (has was_member flag)
                SELECT e.year, r.angler_id, r.was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler1) - use current member status
                SELECT e.year, tr.angler1_id as angler_id, a.member as was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                JOIN anglers a ON tr.angler1_id = a.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (angler2, when present)
                SELECT e.year, tr.angler2_id as angler_id, a.member as was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                JOIN anglers a ON tr.angler2_id = a.id
                WHERE t.complete = true AND tr.angler2_id IS NOT NULL
            )
            SELECT
                ap.year,
                COUNT(DISTINCT CASE WHEN ap.was_member = true THEN ap.angler_id END) as member_count,
                COUNT(DISTINCT CASE WHEN ap.was_member = false THEN ap.angler_id END) as guest_count,
                COUNT(DISTINCT ap.angler_id) as total_anglers
            FROM all_participants ap
            GROUP BY ap.year
            ORDER BY ap.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_weight_trends_by_year(self) -> List[Dict[str, Any]]:
        """Get average weights per tournament by year."""
        # Combines both individual results and team_results
        query = """
            WITH all_results AS (
                -- Individual format results
                SELECT t.id as tournament_id, e.year, r.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team format results (per boat)
                SELECT t.id as tournament_id, e.year, tr.total_weight
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN team_results tr ON tr.tournament_id = t.id
                WHERE t.complete = true
            )
            SELECT
                ar.year,
                CASE
                    WHEN COUNT(*) > 0
                    THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(*)
                    ELSE 0
                END as avg_individual_weight,
                CASE
                    WHEN COUNT(DISTINCT ar.tournament_id) > 0
                    THEN COALESCE(SUM(ar.total_weight), 0) / COUNT(DISTINCT ar.tournament_id)
                    ELSE 0
                END as avg_tournament_total_weight,
                MAX(ar.total_weight) as max_individual_weight
            FROM all_results ar
            GROUP BY ar.year
            ORDER BY ar.year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_winning_weights_by_year(self) -> List[Dict[str, Any]]:
        """Get average 1st, 2nd, 3rd place weights by year."""
        # Combines both individual results and team_results
        query = """
            WITH ranked_results AS (
                -- Individual format results
                SELECT
                    e.year,
                    t.id as tournament_id,
                    r.total_weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY r.total_weight DESC
                    ) as place
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE t.complete = true
                    AND r.disqualified = false
                    AND r.total_weight > 0
                UNION ALL
                -- Team format results (use place_finish if available, otherwise rank by weight)
                SELECT
                    e.year,
                    t.id as tournament_id,
                    tr.total_weight,
                    COALESCE(tr.place_finish, ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY tr.total_weight DESC
                    )) as place
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                WHERE t.complete = true
                    AND tr.total_weight > 0
            )
            SELECT
                year,
                AVG(CASE WHEN place = 1 THEN total_weight END) as avg_1st,
                AVG(CASE WHEN place = 2 THEN total_weight END) as avg_2nd,
                AVG(CASE WHEN place = 3 THEN total_weight END) as avg_3rd
            FROM ranked_results
            WHERE place <= 3
            GROUP BY year
            ORDER BY year ASC
        """
        return self._fetch_all_converted(query, {})

    def get_winning_weights_by_lake(self) -> List[Dict[str, Any]]:
        """Get avg 1st, 2nd, 3rd place weights and tournament count per lake."""
        # Combines both individual results and team_results
        query = """
            WITH ranked_results AS (
                -- Individual format results
                SELECT
                    l.id as lake_id,
                    l.display_name as lake_name,
                    t.id as tournament_id,
                    r.total_weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY r.total_weight DESC
                    ) as place
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN lakes l ON t.lake_id = l.id
                WHERE t.complete = true
                    AND r.disqualified = false
                    AND r.total_weight > 0
                UNION ALL
                -- Team format results
                SELECT
                    l.id as lake_id,
                    l.display_name as lake_name,
                    t.id as tournament_id,
                    tr.total_weight,
                    COALESCE(tr.place_finish, ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY tr.total_weight DESC
                    )) as place
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN lakes l ON t.lake_id = l.id
                WHERE t.complete = true
                    AND tr.total_weight > 0
            )
            SELECT
                lake_name,
                AVG(CASE WHEN place = 1 THEN total_weight END) as avg_1st,
                AVG(CASE WHEN place = 2 THEN total_weight END) as avg_2nd,
                AVG(CASE WHEN place = 3 THEN total_weight END) as avg_3rd,
                COUNT(DISTINCT tournament_id) as tournament_count
            FROM ranked_results
            WHERE place <= 3
            GROUP BY lake_id, lake_name
            ORDER BY avg_1st DESC
        """
        return self._fetch_all_converted(query, {})

    def get_tournament_participation(self) -> List[Dict[str, Any]]:
        """Get participation counts per tournament with member counts."""
        # Uses individual results as primary source for accurate per-angler stats
        # Falls back to team_results only for tournaments without results data
        # Also includes cancelled tournaments with 0 participants
        query = """
            WITH all_participants AS (
                -- Individual results (primary source with was_member flag)
                SELECT t.id as tournament_id, e.year, e.date, l.display_name as lake_name,
                       r.angler_id, r.was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN lakes l ON t.lake_id = l.id
                JOIN results r ON r.tournament_id = t.id
                WHERE t.complete = true
                UNION ALL
                -- Team results angler1 (only for tournaments without individual data)
                SELECT t.id as tournament_id, e.year, e.date, l.display_name as lake_name,
                       tr.angler1_id as angler_id, a.member as was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN lakes l ON t.lake_id = l.id
                JOIN team_results tr ON tr.tournament_id = t.id
                JOIN anglers a ON tr.angler1_id = a.id
                WHERE t.complete = true
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
                UNION ALL
                -- Team results angler2 (only for tournaments without individual data)
                SELECT t.id as tournament_id, e.year, e.date, l.display_name as lake_name,
                       tr.angler2_id as angler_id, a.member as was_member
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                JOIN lakes l ON t.lake_id = l.id
                JOIN team_results tr ON tr.tournament_id = t.id
                JOIN anglers a ON tr.angler2_id = a.id
                WHERE t.complete = true
                  AND tr.angler2_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM results r WHERE r.tournament_id = t.id)
            ),
            cancelled_tournaments AS (
                -- Cancelled tournaments show as 0 participants
                SELECT e.id as event_id, e.year, e.date,
                       COALESCE(e.lake_name, 'Cancelled') as lake_name
                FROM events e
                WHERE e.is_cancelled = true
                  AND e.event_type IN ('sabc_tournament', 'other_tournament')
            ),
            combined AS (
                -- Completed tournaments with participants
                SELECT
                    ap.tournament_id,
                    ap.year,
                    ap.date,
                    ap.lake_name,
                    COUNT(DISTINCT ap.angler_id) as participants,
                    COUNT(DISTINCT CASE WHEN ap.was_member = true THEN ap.angler_id END) as members,
                    COUNT(DISTINCT CASE WHEN ap.was_member = false THEN ap.angler_id END) as guests
                FROM all_participants ap
                GROUP BY ap.tournament_id, ap.year, ap.date, ap.lake_name
                UNION ALL
                -- Cancelled tournaments with 0 participants
                SELECT
                    NULL as tournament_id,
                    ct.year,
                    ct.date,
                    ct.lake_name,
                    0 as participants,
                    0 as members,
                    0 as guests
                FROM cancelled_tournaments ct
            )
            SELECT
                c.tournament_id,
                c.year,
                TO_CHAR(c.date, 'YYYY-MM-DD') as tournament_date,
                c.lake_name,
                c.participants,
                c.members,
                c.guests
            FROM combined c
            ORDER BY c.date ASC
        """
        return self._fetch_all_converted(query, {})

    def get_winning_weights_by_lake_year(self) -> List[Dict[str, Any]]:
        """Get 1st, 2nd, 3rd place weights by lake for each year."""
        # Combines both individual results and team_results
        query = """
            WITH ranked_results AS (
                -- Individual format results
                SELECT
                    e.year,
                    l.display_name as lake_name,
                    t.id as tournament_id,
                    r.total_weight,
                    ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY r.total_weight DESC
                    ) as place
                FROM results r
                JOIN tournaments t ON r.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                JOIN lakes l ON t.lake_id = l.id
                WHERE t.complete = true
                    AND r.disqualified = false
                    AND r.total_weight > 0
                UNION ALL
                -- Team format results
                SELECT
                    e.year,
                    l.display_name as lake_name,
                    t.id as tournament_id,
                    tr.total_weight,
                    COALESCE(tr.place_finish, ROW_NUMBER() OVER (
                        PARTITION BY t.id
                        ORDER BY tr.total_weight DESC
                    )) as place
                FROM team_results tr
                JOIN tournaments t ON tr.tournament_id = t.id
                JOIN events e ON t.event_id = e.id
                JOIN lakes l ON t.lake_id = l.id
                WHERE t.complete = true
                    AND tr.total_weight > 0
            )
            SELECT
                year,
                lake_name,
                AVG(CASE WHEN place = 1 THEN total_weight END) as avg_1st,
                AVG(CASE WHEN place = 2 THEN total_weight END) as avg_2nd,
                AVG(CASE WHEN place = 3 THEN total_weight END) as avg_3rd,
                COUNT(DISTINCT tournament_id) as tournament_count
            FROM ranked_results
            WHERE place <= 3
            GROUP BY year, lake_name
            ORDER BY year DESC, avg_1st DESC
        """
        return self._fetch_all_converted(query, {})
