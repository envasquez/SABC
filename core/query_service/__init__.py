"""
Consolidated query service to reduce code duplication.
Combines functionality from queries.py, common_queries.py, and other query modules.
"""

from sqlalchemy import Connection

from core.query_service.event_queries import EventQueries
from core.query_service.lake_queries import LakeQueries
from core.query_service.member_queries import MemberQueries
from core.query_service.poll_queries import PollQueries
from core.query_service.tournament_queries import TournamentQueries
from core.query_service.user_queries import UserQueries


class QueryService(
    UserQueries,
    LakeQueries,
    PollQueries,
    TournamentQueries,
    EventQueries,
    MemberQueries,
):
    """Centralized database query service combining all query categories."""

    def __init__(self, conn: Connection):
        super().__init__(conn)


__all__ = ["QueryService"]
