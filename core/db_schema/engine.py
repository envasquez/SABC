import os

from sqlalchemy import create_engine

_env = os.environ.get("ENVIRONMENT", "development")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    if _env == "production":
        raise RuntimeError("DATABASE_URL must be set in production")
    DATABASE_URL = "postgresql://postgres:dev123@localhost:5432/sabc"

# Enforce SSL for production database connections
if _env == "production" and "sslmode=" not in DATABASE_URL:
    separator = "&" if "?" in DATABASE_URL else "?"
    DATABASE_URL += f"{separator}sslmode=require"

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
)
