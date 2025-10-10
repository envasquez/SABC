"""Alembic environment configuration for SABC database migrations."""

import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context  # type: ignore[attr-defined]

# Add project root to sys.path to import SABC modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# ruff: noqa: E402 - Must modify sys.path before importing SABC modules
from core.db_schema.models import Base

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target_metadata to the Base metadata from SABC models
# This enables autogenerate to detect model changes
target_metadata = Base.metadata

# Get database URL from environment variable (same as SABC app uses)
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc")

# Override the sqlalchemy.url from alembic.ini with environment variable
config.set_main_option("sqlalchemy.url", DATABASE_URL)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,  # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
