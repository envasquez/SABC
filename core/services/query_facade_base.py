"""Base query service facade with core execution methods."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Connection

from core.services.user_service import UserService


class QueryFacadeBase:
    """Base facade with core query execution methods."""

    def __init__(self, conn: Connection):
        self.conn = conn
        self._user_service = UserService(conn)

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._user_service.execute(query, params)

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        return self._user_service.fetch_all(query, params)

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        return self._user_service.fetch_one(query, params)

    def fetch_value(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self._user_service.fetch_value(query, params)
