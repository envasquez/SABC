"""Tournament-related database queries with full type safety."""

from typing import Any, Dict, List, Optional

from core.query_service.base import QueryServiceBase


class TournamentQueries(QueryServiceBase):
    """Query service for tournament database operations."""

    def get_tournament_by_id(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        """
        Get tournament by ID with event details.

        Args:
            tournament_id: Tournament ID to fetch

        Returns:
            Tournament dictionary with event date and name, or None if not found
        """
        return self.fetch_one(
            """
            SELECT t.*, e.date, e.name
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE t.id = :id
        """,
            {"id": tournament_id},
        )

    def get_tournament_results(self, tournament_id: int) -> List[Dict[str, Any]]:
        """
        Get all results for a tournament with angler details.

        Args:
            tournament_id: Tournament ID to fetch results for

        Returns:
            List of result dictionaries ordered by total weight (net weight) descending
        """
        return self.fetch_all(
            """
            SELECT r.*, a.name as angler_name, a.member
            FROM results r
            JOIN anglers a ON r.angler_id = a.id
            WHERE r.tournament_id = :tournament_id AND a.name != 'Admin User'
            ORDER BY r.total_weight DESC, r.big_bass_weight DESC
        """,
            {"tournament_id": tournament_id},
        )

    def upsert_result(
        self,
        tournament_id: int,
        angler_id: int,
        num_fish: int,
        total_weight: float,
        big_bass_weight: float = 0.0,
        dead_fish_penalty: float = 0.0,
        disqualified: bool = False,
        buy_in: bool = False,
    ) -> None:
        """
        Insert or update tournament result for an angler.

        Args:
            tournament_id: Tournament ID
            angler_id: Angler ID
            num_fish: Number of fish caught
            total_weight: Total weight in pounds
            big_bass_weight: Weight of biggest bass in pounds
            dead_fish_penalty: Penalty weight for dead fish
            disqualified: Whether angler was disqualified
            buy_in: Whether this was a buy-in entry
        """
        self.execute(
            """
            INSERT INTO results (
                tournament_id, angler_id, num_fish, total_weight,
                big_bass_weight, dead_fish_penalty, disqualified, buy_in
            )
            VALUES (
                :tid, :aid, :fish, :weight, :bass, :penalty, :dq, :buy
            )
            ON CONFLICT (tournament_id, angler_id)
            DO UPDATE SET
                num_fish = EXCLUDED.num_fish,
                total_weight = EXCLUDED.total_weight,
                big_bass_weight = EXCLUDED.big_bass_weight,
                dead_fish_penalty = EXCLUDED.dead_fish_penalty,
                disqualified = EXCLUDED.disqualified,
                buy_in = EXCLUDED.buy_in
        """,
            {
                "tid": tournament_id,
                "aid": angler_id,
                "fish": num_fish,
                "weight": total_weight,
                "bass": big_bass_weight,
                "penalty": dead_fish_penalty,
                "dq": disqualified,
                "buy": buy_in,
            },
        )

    def get_team_results(self, tournament_id: int) -> List[Dict[str, Any]]:
        """
        Get team results for a tournament with combined weights.

        For team format tournaments (no individual results), uses stored values
        from team_results. For standard format, calculates from individual results.

        Args:
            tournament_id: Tournament ID to fetch team results for

        Returns:
            List of team result dictionaries ordered by total weight descending
        """
        query = """
            SELECT tr.id, tr.tournament_id, tr.angler1_id, tr.angler2_id, tr.place_finish,
                   a1.name as angler1_name, a1.member as angler1_member,
                   a2.name as angler2_name, a2.member as angler2_member,
                   CASE
                       WHEN r1.id IS NULL AND r2.id IS NULL THEN COALESCE(tr.num_fish, 0)
                       ELSE COALESCE(r1.num_fish, 0) + COALESCE(r2.num_fish, 0)
                   END as total_fish,
                   CASE
                       WHEN r1.id IS NULL AND r2.id IS NULL THEN COALESCE(tr.total_weight, 0)
                       ELSE COALESCE(r1.total_weight, 0) + COALESCE(r2.total_weight, 0)
                   END as total_weight,
                   COALESCE(r1.was_member, TRUE) as angler1_was_member,
                   COALESCE(r2.was_member, TRUE) as angler2_was_member
            FROM team_results tr
            JOIN anglers a1 ON tr.angler1_id = a1.id
            LEFT JOIN anglers a2 ON tr.angler2_id = a2.id
            LEFT JOIN results r1 ON tr.angler1_id = r1.angler_id
                AND tr.tournament_id = r1.tournament_id
            LEFT JOIN results r2 ON tr.angler2_id = r2.angler_id
                AND tr.tournament_id = r2.tournament_id
            WHERE tr.tournament_id = :tournament_id
            AND a1.name != 'Admin User'
            AND (a2.name != 'Admin User' OR a2.name IS NULL)
            AND COALESCE(r1.buy_in, FALSE) = FALSE
            AND COALESCE(r2.buy_in, FALSE) = FALSE
            ORDER BY CASE
                WHEN r1.id IS NULL AND r2.id IS NULL THEN COALESCE(tr.total_weight, 0)
                ELSE COALESCE(r1.total_weight, 0) + COALESCE(r2.total_weight, 0)
            END DESC
        """
        return self.fetch_all(query, {"tournament_id": tournament_id})

    def get_next_tournament_id(self, tournament_id: int) -> Optional[int]:
        """
        Get the ID of the next tournament chronologically.

        Args:
            tournament_id: Current tournament ID

        Returns:
            Next tournament ID, or None if this is the last tournament
        """
        result = self.fetch_one(
            """
            SELECT t.id
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE t.id > :tournament_id
            ORDER BY e.date ASC, t.id ASC
            LIMIT 1
        """,
            {"tournament_id": tournament_id},
        )
        return result["id"] if result else None

    def get_previous_tournament_id(self, tournament_id: int) -> Optional[int]:
        """
        Get the ID of the previous tournament chronologically.

        Args:
            tournament_id: Current tournament ID

        Returns:
            Previous tournament ID, or None if this is the first tournament
        """
        result = self.fetch_one(
            """
            SELECT t.id
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE t.id < :tournament_id
            ORDER BY e.date DESC, t.id DESC
            LIMIT 1
        """,
            {"tournament_id": tournament_id},
        )
        return result["id"] if result else None

    def get_tournament_years_with_first_id(self, items_per_page: int = 4) -> List[Dict[str, Any]]:
        """
        Get years with pagination info for tournament history navigation.

        Args:
            items_per_page: Number of tournaments per page (default 4)

        Returns:
            List with year, first_tournament_id, and page_number for each year
        """
        # Detect database dialect and use appropriate year extraction function
        dialect_name = self.conn.dialect.name

        if dialect_name == "sqlite":
            # SQLite uses strftime('%Y', date)
            year_expr = "CAST(strftime('%Y', e.date) AS INTEGER)"
        else:
            # PostgreSQL uses EXTRACT(YEAR FROM date)
            year_expr = "EXTRACT(YEAR FROM e.date)::int"

        # Security note: year_expr contains only hardcoded SQL fragments, not user input
        query = f"""
            WITH ranked_tournaments AS (
                SELECT {year_expr} AS year,
                       t.id,
                       ROW_NUMBER() OVER (ORDER BY e.date DESC, t.id DESC) as overall_row,
                       ROW_NUMBER() OVER (PARTITION BY {year_expr} ORDER BY e.date ASC, t.id ASC) as year_row
                FROM tournaments t
                JOIN events e ON t.event_id = e.id
                WHERE t.complete = TRUE
                  AND e.event_type = 'sabc_tournament'
            )
            SELECT year,
                   id as first_tournament_id,
                   CAST(CEIL(CAST(overall_row AS REAL) / :items_per_page) AS INTEGER) as page_number
            FROM ranked_tournaments
            WHERE year_row = 1
            ORDER BY year DESC
        """

        return self.fetch_all(query, {"items_per_page": items_per_page})  # nosec B608
