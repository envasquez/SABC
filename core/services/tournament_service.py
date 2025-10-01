"""Tournament service for tournament-related database operations."""

from typing import Any, Dict, List, Optional

from core.services.base import BaseService
from core.services.tournament_points import calculate_tournament_points


class TournamentService(BaseService):
    """Tournament query methods."""

    def get_tournament_by_id(self, tournament_id: int) -> Optional[dict]:
        """Get tournament details."""
        return self.fetch_one(
            "SELECT t.*, e.date, e.name FROM tournaments t "
            "JOIN events e ON t.event_id = e.id WHERE t.id = :id",
            {"id": tournament_id},
        )

    def get_tournament_results(self, tournament_id: int) -> list[dict]:
        """Get results for a tournament."""
        return self.fetch_all(
            "SELECT r.*, a.name as angler_name, a.member FROM results r "
            "JOIN anglers a ON r.angler_id = a.id "
            "WHERE r.tournament_id = :tournament_id AND a.name != 'Admin User' "
            "ORDER BY r.total_weight DESC",
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
        """Insert or update a tournament result."""
        self.execute(
            "INSERT INTO results (tournament_id, angler_id, num_fish, total_weight, "
            "big_bass_weight, dead_fish_penalty, disqualified, buy_in) "
            "VALUES (:tid, :aid, :fish, :weight, :bass, :penalty, :dq, :buy) "
            "ON CONFLICT (tournament_id, angler_id) DO UPDATE SET "
            "num_fish = EXCLUDED.num_fish, total_weight = EXCLUDED.total_weight, "
            "big_bass_weight = EXCLUDED.big_bass_weight, dead_fish_penalty = EXCLUDED.dead_fish_penalty, "
            "disqualified = EXCLUDED.disqualified, buy_in = EXCLUDED.buy_in",
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
        """Get team results for a tournament."""
        return self.fetch_all(
            "SELECT tr.*, a1.name as angler1_name, a1.member as angler1_member, "
            "a2.name as angler2_name, a2.member as angler2_member, "
            "COALESCE(r1.num_fish, 0) + COALESCE(r2.num_fish, 0) as total_fish "
            "FROM team_results tr "
            "JOIN anglers a1 ON tr.angler1_id = a1.id "
            "JOIN anglers a2 ON tr.angler2_id = a2.id "
            "LEFT JOIN results r1 ON tr.angler1_id = r1.angler_id AND tr.tournament_id = r1.tournament_id "
            "LEFT JOIN results r2 ON tr.angler2_id = r2.angler_id AND tr.tournament_id = r2.tournament_id "
            "WHERE tr.tournament_id = :tournament_id "
            "AND a1.name != 'Admin User' AND a2.name != 'Admin User' "
            "ORDER BY tr.total_weight DESC",
            {"tournament_id": tournament_id},
        )

    def calculate_tournament_points(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Calculate tournament points for results."""
        return calculate_tournament_points(results)
