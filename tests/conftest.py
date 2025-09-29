"""Pytest configuration and fixtures for SABC tests."""

import os
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

# Set test database URL before importing app
os.environ["DATABASE_URL"] = "postgresql://postgres:dev123@localhost:5432/sabc_test"

from app import app  # noqa: E402
from core.db_schema import get_table_definitions  # noqa: E402

TEST_DATABASE_URL = "postgresql://postgres:dev123@localhost:5432/sabc_test"


@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine."""
    engine = create_engine(TEST_DATABASE_URL, echo=False)
    return engine


@pytest.fixture(scope="function")
def db_conn(test_engine) -> Generator[Connection, None, None]:
    """Provide a clean database connection for each test."""
    # Create all tables
    with test_engine.connect() as conn:
        # Drop all tables first
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
        conn.commit()

        # Create fresh tables
        table_definitions = get_table_definitions()
        for table_def in table_definitions:
            conn.execute(text(f"CREATE TABLE IF NOT EXISTS {table_def}"))
        conn.commit()

        yield conn

        # Cleanup after test
        conn.rollback()


@pytest.fixture
def client(db_conn) -> TestClient:
    """Provide a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def admin_user(db_conn) -> dict:
    """Create and return an admin user for testing."""
    import bcrypt

    password_hash = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode("utf-8")

    result = db_conn.execute(
        text("""
            INSERT INTO anglers (name, email, password_hash, member, is_admin, year_joined)
            VALUES (:name, :email, :password_hash, true, true, 2024)
            RETURNING id, name, email, member, is_admin
        """),
        {
            "name": "Test Admin",
            "email": "admin@test.com",
            "password_hash": password_hash,
        },
    )
    db_conn.commit()

    user_data = result.fetchone()
    return {
        "id": user_data[0],
        "name": user_data[1],
        "email": user_data[2],
        "member": user_data[3],
        "is_admin": user_data[4],
        "password": "admin123",
    }


@pytest.fixture
def member_user(db_conn) -> dict:
    """Create and return a regular member user for testing."""
    import bcrypt

    password_hash = bcrypt.hashpw(b"member123", bcrypt.gensalt()).decode("utf-8")

    result = db_conn.execute(
        text("""
            INSERT INTO anglers (name, email, password_hash, member, is_admin, year_joined)
            VALUES (:name, :email, :password_hash, true, false, 2024)
            RETURNING id, name, email, member, is_admin
        """),
        {
            "name": "Test Member",
            "email": "member@test.com",
            "password_hash": password_hash,
        },
    )
    db_conn.commit()

    user_data = result.fetchone()
    return {
        "id": user_data[0],
        "name": user_data[1],
        "email": user_data[2],
        "member": user_data[3],
        "is_admin": user_data[4],
        "password": "member123",
    }


@pytest.fixture
def guest_user(db_conn) -> dict:
    """Create and return a guest user for testing."""
    result = db_conn.execute(
        text("""
            INSERT INTO anglers (name, email, member, is_admin)
            VALUES (:name, :email, false, false)
            RETURNING id, name, email, member, is_admin
        """),
        {
            "name": "Test Guest",
            "email": "guest@test.com",
        },
    )
    db_conn.commit()

    user_data = result.fetchone()
    return {
        "id": user_data[0],
        "name": user_data[1],
        "email": user_data[2],
        "member": user_data[3],
        "is_admin": user_data[4],
    }


@pytest.fixture
def tournament_data(db_conn, admin_user) -> dict:
    """Create event and tournament for testing."""
    from datetime import date

    # Create event
    event_result = db_conn.execute(
        text("""
            INSERT INTO events (date, year, name, event_type)
            VALUES (:date, :year, :name, :event_type)
            RETURNING id
        """),
        {
            "date": date(2024, 6, 15),
            "year": 2024,
            "name": "Test Tournament",
            "event_type": "sabc_tournament",
        },
    )
    event_id = event_result.fetchone()[0]

    # Create tournament
    tournament_result = db_conn.execute(
        text("""
            INSERT INTO tournaments (event_id, name, lake_name, ramp_name, complete)
            VALUES (:event_id, :name, :lake_name, :ramp_name, false)
            RETURNING id
        """),
        {
            "event_id": event_id,
            "name": "Test Tournament",
            "lake_name": "Test Lake",
            "ramp_name": "Test Ramp",
        },
    )
    tournament_id = tournament_result.fetchone()[0]
    db_conn.commit()

    return {
        "event_id": event_id,
        "tournament_id": tournament_id,
    }
