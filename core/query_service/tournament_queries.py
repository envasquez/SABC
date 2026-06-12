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
        """All per-angler results for a tournament with angler details.

        Sourced from v_angler_tournament_results, which projects team-format
        rows alongside individual ones. The view bakes in the Admin User
        exclusion. JOINs results back when present for downstream code that
        reads dead_fish_penalty / id / etc.
        """
        return self.fetch_all(
            """
            SELECT vatr.tournament_id, vatr.angler_id, vatr.num_fish,
                   vatr.total_weight, vatr.big_bass_weight, vatr.dead_fish_penalty,
                   vatr.disqualified, vatr.buy_in, vatr.was_member,
                   r.id, a.name as angler_name, a.member
            FROM v_angler_tournament_results vatr
            JOIN anglers a ON vatr.angler_id = a.id
            LEFT JOIN results r ON r.tournament_id = vatr.tournament_id
                AND r.angler_id = vatr.angler_id
            WHERE vatr.tournament_id = :tournament_id
            ORDER BY vatr.total_weight DESC, vatr.big_bass_weight DESC
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

        Sourced from v_team_tournament_results filtered to ``source =
        'team_results'`` to preserve the original behavior (only return
        rows for tournaments that actually have team_results entries — the
        view also yields synthetic boats-of-one from individual results,
        which we do NOT want here). Joins team_results back for the row id
        used by the admin edit-team-result UI link. The was_member flags
        come from the per-angler results rows when available, defaulting
        to TRUE for the team-format case where no individual row exists.
        """
        query = """
            SELECT tr.id, vttr.tournament_id, vttr.angler1_id, vttr.angler2_id,
                   vttr.place_finish,
                   a1.name as angler1_name, a1.member as angler1_member,
                   a2.name as angler2_name, a2.member as angler2_member,
                   vttr.num_fish as total_fish,
                   vttr.total_weight,
                   vttr.big_bass_weight,
                   COALESCE(r1.was_member, TRUE) as angler1_was_member,
                   COALESCE(r2.was_member, TRUE) as angler2_was_member
            FROM v_team_tournament_results vttr
            JOIN team_results tr ON tr.tournament_id = vttr.tournament_id
                AND tr.angler1_id = vttr.angler1_id
                AND ((tr.angler2_id IS NULL AND vttr.angler2_id IS NULL)
                     OR tr.angler2_id = vttr.angler2_id)
            JOIN anglers a1 ON vttr.angler1_id = a1.id
            LEFT JOIN anglers a2 ON vttr.angler2_id = a2.id
            LEFT JOIN results r1 ON vttr.angler1_id = r1.angler_id
                AND vttr.tournament_id = r1.tournament_id
            LEFT JOIN results r2 ON vttr.angler2_id = r2.angler_id
                AND vttr.tournament_id = r2.tournament_id
            WHERE vttr.tournament_id = :tournament_id
              AND vttr.source = 'team_results'
              AND COALESCE(r1.buy_in, FALSE) = FALSE
              AND COALESCE(r2.buy_in, FALSE) = FALSE
            ORDER BY vttr.total_weight DESC
        """
        return self.fetch_all(query, {"tournament_id": tournament_id})

    def get_next_tournament_id(self, tournament_id: int, current_date: Any) -> Optional[int]:
        """
        Get the ID of the next tournament chronologically.

        Navigation is ordered by event date (with id as a tie-breaker), NOT by
        the raw tournament id, since ids are insertion order and do not track
        the event calendar. Cancelled events are skipped.

        Args:
            tournament_id: Current tournament ID
            current_date: Current tournament's event date

        Returns:
            Next tournament ID, or None if this is the last tournament
        """
        result = self.fetch_one(
            """
            SELECT t.id
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE e.is_cancelled IS NOT TRUE
              AND (e.date > :current_date
                   OR (e.date = :current_date AND t.id > :tournament_id))
            ORDER BY e.date ASC, t.id ASC
            LIMIT 1
        """,
            {"tournament_id": tournament_id, "current_date": current_date},
        )
        return result["id"] if result else None

    def get_previous_tournament_id(self, tournament_id: int, current_date: Any) -> Optional[int]:
        """
        Get the ID of the previous tournament chronologically.

        Navigation is ordered by event date (with id as a tie-breaker), NOT by
        the raw tournament id, since ids are insertion order and do not track
        the event calendar. Cancelled events are skipped.

        Args:
            tournament_id: Current tournament ID
            current_date: Current tournament's event date

        Returns:
            Previous tournament ID, or None if this is the first tournament
        """
        result = self.fetch_one(
            """
            SELECT t.id
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE e.is_cancelled IS NOT TRUE
              AND (e.date < :current_date
                   OR (e.date = :current_date AND t.id < :tournament_id))
            ORDER BY e.date DESC, t.id DESC
            LIMIT 1
        """,
            {"tournament_id": tournament_id, "current_date": current_date},
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
