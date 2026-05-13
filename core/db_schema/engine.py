import os

from sqlalchemy import create_engine

_env = os.environ.get("ENVIRONMENT", "development")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    if _env == "production":
        raise RuntimeError("DATABASE_URL must be set in production")
    DATABASE_URL = "postgresql://postgres:dev123@localhost:5432/sabc"

# Per-worker pool budget. With gunicorn workers=4, total max DB connections is
# workers * (DB_POOL_SIZE + DB_MAX_OVERFLOW). Old defaults (10+20) put us at
# 120 max, over Postgres' default max_connections=100. New defaults (5+10) cap
# at 60 with workers=4. Override via env if you bump workers or know the
# Postgres instance allows more.
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
