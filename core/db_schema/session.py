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


def get_db_session() -> Generator[Session, None, None]:
    """Get a database session (use with dependency injection).

    Usage in FastAPI:
        @router.get("/")
        def route(session: Session = Depends(get_db_session)):
            ...
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
