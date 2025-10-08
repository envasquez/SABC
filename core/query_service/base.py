"""Base query service class with common database operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy import Connection, text


class QueryServiceBase:
    """Base class for all query service classes with common database methods."""

    def __init__(self, conn: Connection) -> None:
        """
        Initialize query service with database connection.

        Args:
            conn: SQLAlchemy database connection
        """
        self.conn = conn

    def execute(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute a SQL query with optional parameters.

        Args:
            query: SQL query string (use :param_name for parameters)
            params: Dictionary of parameter names and values

        Returns:
            SQLAlchemy result object
        """
        return self.conn.execute(text(query), params or {})

    def fetch_all(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute query and return all results as list of dictionaries.

        Args:
            query: SQL query string (use :param_name for parameters)
            params: Dictionary of parameter names and values

        Returns:
            List of row dictionaries
        """
        result = self.execute(query, params)
        return [dict(row._mapping) for row in result]

    def fetch_one(
        self, query: str, params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Execute query and return first result as dictionary.

        Args:
            query: SQL query string (use :param_name for parameters)
            params: Dictionary of parameter names and values

        Returns:
            First row as dictionary, or None if no results
        """
        results = self.fetch_all(query, params)
        return results[0] if results else None

    def fetch_value(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """
        Execute query and return first column of first row.

        Args:
            query: SQL query string (use :param_name for parameters)
            params: Dictionary of parameter names and values

        Returns:
            Value of first column in first row, or None if no results
        """
        result = self.fetch_one(query, params)
        if result:
            return next(iter(result.values()))
        return None
