"""User-related methods for query service facade."""

from typing import Any, Dict, Optional

from sqlalchemy import Connection

from core.services.query_facade_base import QueryFacadeBase
from core.services.user_service import UserService


class QueryFacadeUser(QueryFacadeBase):
    """User query delegation methods."""

    def __init__(self, conn: Connection):
        super().__init__(conn)
        self._user_service = UserService(conn)

    def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return self._user_service.get_user_by_email(email)

    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        return self._user_service.get_user_by_id(user_id)

    def update_user(self, user_id: int, updates: dict) -> None:
        return self._user_service.update_user(user_id, updates)

    def create_user(
        self,
        name: str,
        email: str,
        password_hash: str,
        member: bool = False,
        is_admin: bool = False,
    ) -> int:
        return self._user_service.create_user(name, email, password_hash, member, is_admin)

    def delete_user(self, user_id: int) -> None:
        return self._user_service.delete_user(user_id)
