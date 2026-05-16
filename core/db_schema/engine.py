import os

from sqlalchemy import create_engine

_env = os.environ.get("ENVIRONMENT", "development")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    if _env == "production":
        raise RuntimeError("DATABASE_URL must be set in production")
    DATABASE_URL = "postgresql://postgres:dev123@localhost:5432/sabc"

# Per-process pool budget. Production runs a single uvicorn worker per
# container, so total max DB connections per web container is
# DB_POOL_SIZE + DB_MAX_OVERFLOW. Defaults (5+10) cap at 15 per container,
# well under Postgres' configured max_connections=200. Override via env if
# you scale to multiple workers/containers or know the Postgres instance
# allows more.
_POOL_SIZE = int(os.environ.get("DB_POOL_SIZE", "5"))
_MAX_OVERFLOW = int(os.environ.get("DB_MAX_OVERFLOW", "10"))

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=_POOL_SIZE,
    max_overflow=_MAX_OVERFLOW,
    pool_recycle=3600,
)
