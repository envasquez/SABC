"""Complete query service facade with all delegations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Connection

from core.services.angler_service import AnglerService
from core.services.event_service import EventService
from core.services.poll_service import PollService
from core.services.query_facade_lake import QueryFacadeLake
from core.services.tournament_service import TournamentService


class QueryService(QueryFacadeLake):
    """Complete query service delegating to all specialized services."""

    def __init__(self, conn: Connection):
        super().__init__(conn)
        self._poll_service = PollService(conn)
        self._tournament_service = TournamentService(conn)
        self._event_service = EventService(conn)
        self._angler_service = AnglerService(conn)

    def get_poll_by_id(self, poll_id: int) -> Optional[dict]:
        return self._poll_service.get_poll_by_id(poll_id)

    def get_active_polls(self) -> list[dict]:
        return self._poll_service.get_active_polls()

    def get_user_vote(self, poll_id: int, user_id: int) -> Optional[dict]:
        return self._poll_service.get_user_vote(poll_id, user_id)

    def get_poll_options_with_votes(
        self, poll_id: int, include_details: bool = False
    ) -> list[dict]:
        return self._poll_service.get_poll_options_with_votes(poll_id, include_details)

    def get_tournament_by_id(self, tournament_id: int) -> Optional[dict]:
        return self._tournament_service.get_tournament_by_id(tournament_id)

    def get_tournament_results(self, tournament_id: int) -> list[dict]:
        return self._tournament_service.get_tournament_results(tournament_id)

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
        return self._tournament_service.upsert_result(
            tournament_id,
            angler_id,
            num_fish,
            total_weight,
            big_bass_weight,
            dead_fish_penalty,
            disqualified,
            buy_in,
        )

    def get_team_results(self, tournament_id: int) -> list[dict]:
        return self._tournament_service.get_team_results(tournament_id)

    def calculate_tournament_points(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self._tournament_service.calculate_tournament_points(results)

    def get_upcoming_events(self) -> list[dict]:
        return self._event_service.get_upcoming_events()

    def get_past_events(self) -> list[dict]:
        return self._event_service.get_past_events()

    def get_admin_events_data(
        self,
        upcoming_limit: int = 20,
        upcoming_offset: int = 0,
        past_limit: int = 20,
        past_offset: int = 0,
    ) -> dict:
        return self._event_service.get_admin_events_data(
            upcoming_limit, upcoming_offset, past_limit, past_offset
        )

    def get_all_members(self) -> list[dict]:
        return self._angler_service.get_all_members()

    def get_all_anglers(self) -> list[dict]:
        return self._angler_service.get_all_anglers()

    def get_admin_anglers_list(self) -> list[dict]:
        return self._angler_service.get_admin_anglers_list()

    def get_angler_stats(self, angler_id: int, year: Optional[int] = None) -> dict:
        return self._angler_service.get_angler_stats(angler_id, year)
