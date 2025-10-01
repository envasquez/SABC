"""Base query service with core execution methods."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Connection, text


class QueryServiceBase:
    """Base database query service with core execution methods."""

    def __init__(self, conn: Connection):
        self.conn = conn

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a raw query with parameters."""
        return self.conn.execute(text(query), params or {})

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Execute query and return all results as list of dicts."""
        result = self.execute(query, params)
        return [dict(row._mapping) for row in result]

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Execute query and return first result as dict or None."""
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def fetch_value(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute query and return single value from first row."""
        result = self.fetch_one(query, params)
        if result:
            return next(iter(result.values()))
        return None
