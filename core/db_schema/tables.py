"""DEPRECATED: Table management functions.

This module is deprecated and should not be used. All database schema changes
must be managed through Alembic migrations.

The functions in this module have been disabled to prevent accidental misuse.
They contained SQL injection risks and are no longer needed.

For schema changes, use: alembic revision --autogenerate -m "description"
"""

import logging
import warnings
from typing import List

logger = logging.getLogger(__name__)


def get_table_definitions() -> List[str]:
    """DEPRECATED: Get table definitions for manual table creation.

    This function is deprecated. Use Alembic migrations instead.

    Returns:
        Empty list (function is deprecated)
    """
    warnings.warn(
        "get_table_definitions() is deprecated. Use Alembic migrations instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return []


def create_all_tables() -> None:
    """DEPRECATED: Create all tables using table definitions.

    This function is deprecated and disabled. Use Alembic migrations instead.

    Raises:
        NotImplementedError: Always raised to prevent usage
    """
    warnings.warn(
        "create_all_tables() is deprecated. Use Alembic migrations instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "Manual table creation is disabled. Use Alembic migrations: "
        "alembic revision --autogenerate -m 'description'"
    )


def drop_all_tables() -> None:
    """DEPRECATED: Drop all tables.

    This function is deprecated and disabled. Use Alembic migrations for
    schema changes, or drop the database and recreate it for testing.

    Raises:
        NotImplementedError: Always raised to prevent usage
    """
    warnings.warn(
        "drop_all_tables() is deprecated and dangerous. "
        "Use Alembic migrations or drop/recreate database for testing.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "Manual table dropping is disabled for safety. "
        "For testing, drop and recreate the database. "
        "For schema changes, use Alembic migrations."
    )


def init_db() -> None:
    """DEPRECATED: Initialize database.

    This function is deprecated. Use Alembic migrations instead.

    Raises:
        NotImplementedError: Always raised to prevent usage
    """
    warnings.warn(
        "init_db() is deprecated. Use Alembic migrations instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    raise NotImplementedError(
        "Manual database initialization is disabled. Use Alembic migrations: alembic upgrade head"
    )
