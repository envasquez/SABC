"""SQLAlchemy session management for database operations."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy.orm import Session, sessionmaker

from core.db_schema.engine import engine

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions.

    Usage:
        with get_session() as session:
            angler = session.query(Angler).filter(Angler.id == 1).first()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# Backwards-compatible alias of `get_session`.
#
# The audit flagged this as a verbatim duplicate of `get_session` with no
# production callers — but it is NOT dead code: tests/conftest.py monkeypatches
# `core.db_schema.session.get_db_session` and `core.db_schema.get_db_session`,
# and `monkeypatch.setattr` requires the attribute to already exist. Deleting
# the symbol would break the test fixture, so it is kept as a thin alias
# instead of a copy-pasted body.
get_db_session = get_session
