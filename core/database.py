from sqlalchemy import text

from core.db_schema import engine


def db(q, p=None):
    with engine.connect() as c:
        # Convert string queries to SQLAlchemy text objects
        if isinstance(q, str):
            query = text(q)
        else:
            query = q

        r = c.execute(query, p or {})
        query_str = str(q).upper()
        if any(kw in query_str for kw in ["INSERT", "UPDATE", "DELETE", "CREATE", "DROP", "ALTER"]):
            c.commit()
        return r.fetchall() if "SELECT" in query_str else r.lastrowid
