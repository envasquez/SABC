from typing import Any, Dict, List, Optional

from sqlalchemy import Connection, text


class QueryServiceBase:
    def __init__(self, conn: Connection):
        self.conn = conn

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        return self.conn.execute(text(query), params or {})

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        result = self.execute(query, params)
        return [dict(row._mapping) for row in result]

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def fetch_value(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        result = self.fetch_one(query, params)
        if result:
            return next(iter(result.values()))
        return None
