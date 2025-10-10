from typing import Any, Dict, List, Optional, Tuple, TypeGuard, Union

from sqlalchemy import TextClause, text

from core.db_schema import engine


def db(
    q: Union[str, TextClause], p: Optional[Dict[str, Any]] = None
) -> Union[List[Tuple[Any, ...]], int]:
    """Execute a database query and return results or row count (DEPRECATED).

    .. deprecated:: 1.0
        Use SQLAlchemy ORM with :func:`get_session` and QueryService instead.
        This function will be removed in a future version.

    Args:
        q: SQL query string or TextClause
        p: Optional parameters dictionary

    Returns:
        For SELECT queries: List of tuples (rows)
        For INSERT/UPDATE/DELETE: Row count (int)
    """
    import warnings

    warnings.warn(
        "db() is deprecated, use SQLAlchemy ORM with get_session() and QueryService instead",
        DeprecationWarning,
        stacklevel=2,
    )
    with engine.connect() as c:
        query = text(q) if isinstance(q, str) else q
        r = c.execute(query, p or {})
        query_str = str(q).upper()
        if any(kw in query_str for kw in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]):
            c.commit()
        if "SELECT" in query_str or "RETURNING" in query_str:
            # Convert Row objects to tuples for better type compatibility
            return [tuple(row) for row in r.fetchall()]
        # For write operations, return affected row count
        return getattr(r, "rowcount", 0) or 0


def is_result_list(result: Union[List[Tuple[Any, ...]], int]) -> TypeGuard[List[Tuple[Any, ...]]]:
    """Type guard to check if db() result is a list of tuples."""
    return isinstance(result, list)
