from typing import Any, Dict, Optional, Sequence, Union

from sqlalchemy import Row, TextClause, text
from sqlalchemy.engine import Result

from core.db_schema import engine


def db(
    q: Union[str, TextClause], p: Optional[Dict[str, Any]] = None
) -> Union[Sequence[Row[Any]], int, None]:
    with engine.connect() as c:
        # Convert string queries to SQLAlchemy text objects
        if isinstance(q, str):
            query = text(q)
        else:
            query = q

        r: Result[Any] = c.execute(query, p or {})
        query_str = str(q).upper()
        if any(kw in query_str for kw in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]):
            c.commit()
        if "SELECT" in query_str:
            return r.fetchall()
        else:
            return r.lastrowid
