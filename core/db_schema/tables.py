import logging
from typing import List

from sqlalchemy import text

from core.db_schema.engine import engine

logger = logging.getLogger(__name__)


def get_table_definitions() -> List[str]:
    """Get table definitions for manual table creation.

    Note: This is currently unused as we use migrations instead.
    """
    return []


def create_all_tables() -> None:
    """Create all tables using table definitions.

    Note: This is currently unused as we use migrations instead.
    """
    logger.info("Creating PostgreSQL database tables...")
    table_definitions = get_table_definitions()

    with engine.connect() as c:
        for table_def in table_definitions:
            c.execute(text(f"CREATE TABLE IF NOT EXISTS {table_def}"))
        c.commit()


def drop_all_tables() -> None:
    logger.info("Dropping all PostgreSQL tables...")
    with engine.connect() as c:
        tables = [
            "password_reset_tokens",
            "poll_votes",
            "poll_options",
            "polls",
            "team_results",
            "results",
            "tournaments",
            "events",
            "ramps",
            "lakes",
            "anglers",
        ]
        for table in tables:
            c.execute(text(f"DROP TABLE IF EXISTS {table} CASCADE"))
        c.commit()


def init_db() -> None:
    create_all_tables()
