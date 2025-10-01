from typing import Optional

from core.query_service.base import QueryServiceBase


class TournamentQueries(QueryServiceBase):
    def auto_complete_past_tournaments(self) -> int:
        result = self.execute(
            """
            UPDATE tournaments t
            SET complete = TRUE
            FROM events e
            WHERE t.event_id = e.id
            AND e.date < CURRENT_DATE
            AND t.complete = FALSE
            """,
        )
        return result.rowcount if result else 0

    def get_tournament_by_id(self, tournament_id: int) -> Optional[dict]:
        return self.fetch_one(
            """
            SELECT t.*, e.date, e.name
            FROM tournaments t
            JOIN events e ON t.event_id = e.id
            WHERE t.id = :id
        """,
            {"id": tournament_id},
        )

    def get_tournament_results(self, tournament_id: int) -> list[dict]:
        return self.fetch_all(
            """
            SELECT r.*, a.name as angler_name, a.member
            FROM results r
            JOIN anglers a ON r.angler_id = a.id
            WHERE r.tournament_id = :tournament_id AND a.name != 'Admin User'
            ORDER BY r.total_weight DESC
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

    def get_team_results(self, tournament_id: int) -> list[dict]:
        query = """
            SELECT tr.*,
                   a1.name as angler1_name, a1.member as angler1_member,
                   a2.name as angler2_name, a2.member as angler2_member,
                   COALESCE(r1.num_fish, 0) + COALESCE(r2.num_fish, 0) as total_fish,
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
            ORDER BY tr.total_weight DESC
        """
        return self.fetch_all(query, {"tournament_id": tournament_id})
