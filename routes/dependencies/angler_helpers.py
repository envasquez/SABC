"""Angler database helper functions."""

from typing import Any, Dict, List

from core.db_schema import engine
from core.query_service import QueryService


def get_admin_anglers_list() -> List[Dict[str, Any]]:
    """Get list of anglers for admin purposes."""
    with engine.connect() as conn:
        qs = QueryService(conn)
        return qs.get_admin_anglers_list()
