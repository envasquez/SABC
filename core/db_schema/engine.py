import os

from sqlalchemy import create_engine

DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://postgres:dev123@localhost:5432/sabc")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
