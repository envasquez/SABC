"""Pytest configuration and shared fixtures for SABC tests."""

import os

# CRITICAL: Set test database URL BEFORE any imports
# This must happen before core.db_schema.engine imports and creates the engine
# Use file-based SQLite so multiple engines can share the same database
TEST_DATABASE_URL = "sqlite:///test_sabc.db"  # File-based SQLite for tests
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ["ENVIRONMENT"] = "test"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-minimum-32-characters-long"
os.environ["DEBUG"] = "false"
os.environ["LOG_LEVEL"] = "ERROR"

# ruff: noqa: E402 - Must set env vars before imports
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, Generator, Optional

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app_routes import register_routes
from app_setup import create_app
from core.db_schema import Angler, Base, Event, Lake, Poll, PollOption, Ramp, Tournament

# Create test engine with in-memory SQLite
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Configure SQLite to handle Decimal types (convert to float for storage)
from decimal import Decimal

from sqlalchemy import event


@event.listens_for(test_engine, "connect")
def set_sqlite_decimal_support(dbapi_conn, connection_record):
    """Add Decimal support to SQLite by registering adapters."""
    import sqlite3

    # Adapter: Convert Decimal to float when storing
    sqlite3.register_adapter(Decimal, lambda d: float(d))

    # Converter: Convert back to Decimal when retrieving (optional, can keep as float)
    # sqlite3.register_converter("DECIMAL", lambda s: Decimal(s.decode('utf-8')))


TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def set_test_environment():
    """Set environment variables for testing."""
    os.environ["ENVIRONMENT"] = "test"
    os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only-minimum-32-characters-long"
    os.environ["DATABASE_URL"] = TEST_DATABASE_URL
    os.environ["DEBUG"] = "false"
    os.environ["LOG_LEVEL"] = "ERROR"  # Reduce noise in test output
    yield
    # Cleanup
    os.environ.pop("ENVIRONMENT", None)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Create a fresh database session for each test.

    This fixture creates all tables, yields a session for the test,
    then rolls back and drops all tables for isolation.
    """
    # Create tables
    Base.metadata.create_all(bind=test_engine)

    # Create session
    session = TestSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop all tables for clean slate
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session, monkeypatch) -> Generator[TestClient, None, None]:
    """
    Create a test client with a fresh database for each test.

    Overrides the database dependency to use the test database.
    """
    # Monkey-patch get_session to use test database
    from contextlib import contextmanager

    @contextmanager
    def mock_get_session():
        """Return test database session."""
        try:
            yield db_session
        finally:
            pass

    # Override both get_session and get_db_session
    monkeypatch.setattr("core.db_schema.session.get_session", mock_get_session)
    monkeypatch.setattr("core.db_schema.get_session", mock_get_session)

    def mock_get_db_session():
        """Return test database session for FastAPI dependency injection."""
        return db_session

    monkeypatch.setattr("core.db_schema.session.get_db_session", mock_get_db_session)
    monkeypatch.setattr("core.db_schema.get_db_session", mock_get_db_session)

    app = create_app()
    register_routes(app)

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def test_password() -> str:
    """Standard test password for all test users."""
    return "TestPassword!@#$Secure9"


@pytest.fixture
def password_hash(test_password: str) -> str:
    """Hashed version of test password."""
    return bcrypt.hashpw(test_password.encode(), bcrypt.gensalt()).decode()


@pytest.fixture
def regular_user(db_session: Session, password_hash: str) -> Angler:
    """Create a regular (non-admin, non-member) user for testing."""
    user = Angler(
        name="Test User",
        email="testuser@example.com",
        password_hash=password_hash,
        member=False,
        is_admin=False,
        created_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def member_user(db_session: Session, password_hash: str) -> Angler:
    """Create a member (non-admin) user for testing with current dues."""
    user = Angler(
        name="Test Member",
        email="member@example.com",
        password_hash=password_hash,
        member=True,
        is_admin=False,
        created_at=datetime.now(tz=timezone.utc),
        dues_paid_through=date.today() + timedelta(days=365),  # Dues valid for a year
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_user(db_session: Session, password_hash: str) -> Angler:
    """Create an admin user for testing."""
    user = Angler(
        name="Test Admin",
        email="admin@example.com",
        password_hash=password_hash,
        member=True,
        is_admin=True,
        created_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_lake(db_session: Session) -> Lake:
    """Create a test lake for testing."""
    lake = Lake(
        yaml_key="test-lake",
        display_name="Test Lake",
        google_maps_iframe="<iframe>test</iframe>",
        created_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(lake)
    db_session.commit()
    db_session.refresh(lake)
    return lake


@pytest.fixture
def test_ramp(db_session: Session, test_lake: Lake) -> Ramp:
    """Create a test boat ramp for testing."""
    ramp = Ramp(
        lake_id=test_lake.id,
        name="Test Ramp",
        google_maps_iframe="<iframe>test ramp</iframe>",
        created_at=datetime.now(tz=timezone.utc),
    )
    db_session.add(ramp)
    db_session.commit()
    db_session.refresh(ramp)
    return ramp


@pytest.fixture
def test_event(db_session: Session, test_lake: Lake, test_ramp: Ramp) -> Event:
    """Create a test event for testing."""
    from datetime import date, time

    event = Event(
        date=date(2025, 11, 15),
        year=2025,
        name="Test Tournament",
        description="Test tournament description",
        event_type="sabc_tournament",
        start_time=time(6, 0),
        weigh_in_time=time(15, 0),
        lake_name=test_lake.display_name,
        ramp_name=test_ramp.name,
        entry_fee=25.00,
        is_cancelled=False,
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event


@pytest.fixture
def test_tournament(
    db_session: Session, test_event: Event, test_lake: Lake, test_ramp: Ramp
) -> Tournament:
    """Create a test tournament for testing."""
    from datetime import time

    tournament = Tournament(
        event_id=test_event.id,
        name=test_event.name,
        lake_id=test_lake.id,
        ramp_id=test_ramp.id,
        lake_name=test_lake.display_name,
        ramp_name=test_ramp.name,
        start_time=time(6, 0),
        end_time=time(15, 0),
        fish_limit=5,
        entry_fee=25.00,
        is_team=True,
        is_paper=False,
        big_bass_carryover=0.0,
        complete=False,
        aoy_points=True,
        limit_type="angler",
    )
    db_session.add(tournament)
    db_session.commit()
    db_session.refresh(tournament)
    return tournament


@pytest.fixture
def test_poll(db_session: Session, test_event: Event, admin_user: Angler) -> Poll:
    """Create a test poll for testing."""
    from datetime import timedelta

    from core.helpers.timezone import now_local

    # Use naive datetime for SQLite compatibility (matches production behavior)
    now = now_local().replace(tzinfo=None)
    poll = Poll(
        title="Test Poll",
        description="Test poll description",
        poll_type="simple",
        event_id=test_event.id,
        created_by=admin_user.id,
        created_at=now,
        starts_at=now - timedelta(days=1),  # Started yesterday
        closes_at=now + timedelta(days=7),  # Closes in 7 days
        closed=False,
        multiple_votes=False,
    )
    db_session.add(poll)
    db_session.commit()
    db_session.refresh(poll)
    return poll


@pytest.fixture
def test_poll_option(db_session: Session, test_poll: Poll) -> PollOption:
    """Create a test poll option for testing."""
    option = PollOption(
        poll_id=test_poll.id,
        option_text="Test Option",
        option_data=None,
        display_order=0,
    )
    db_session.add(option)
    db_session.commit()
    db_session.refresh(option)
    return option


@pytest.fixture
def authenticated_client(
    client: TestClient, regular_user: Angler, test_password: str
) -> TestClient:
    """Return a test client with an authenticated regular user session."""
    # First, get the login page to obtain CSRF token
    login_page = client.get("/login")
    csrf_token_cookie = login_page.cookies.get("csrf_token")
    csrf_token = csrf_token_cookie if csrf_token_cookie is not None else ""

    # Now login with CSRF token
    response = client.post(
        "/login",
        data={
            "email": regular_user.email or "",
            "password": test_password,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    if response.status_code not in [302, 303, 307]:
        raise RuntimeError(
            f"Login failed with status {response.status_code}: {response.text[:200]}"
        )
    return client


@pytest.fixture
def member_client(client: TestClient, member_user: Angler, test_password: str) -> TestClient:
    """Return a test client with an authenticated member session."""
    # First, get the login page to obtain CSRF token
    login_page = client.get("/login")
    csrf_token_cookie = login_page.cookies.get("csrf_token")
    csrf_token = csrf_token_cookie if csrf_token_cookie is not None else ""

    # Now login with CSRF token
    response = client.post(
        "/login",
        data={
            "email": member_user.email or "",
            "password": test_password,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    if response.status_code not in [302, 303, 307]:
        raise RuntimeError(
            f"Login failed with status {response.status_code}: {response.text[:200]}"
        )
    return client


@pytest.fixture
def admin_client(client: TestClient, admin_user: Angler, test_password: str) -> TestClient:
    """Return a test client with an authenticated admin session."""
    # First, get the login page to obtain CSRF token
    login_page = client.get("/login")
    csrf_token_cookie = login_page.cookies.get("csrf_token")
    csrf_token = csrf_token_cookie if csrf_token_cookie is not None else ""

    # Now login with CSRF token
    response = client.post(
        "/login",
        data={
            "email": admin_user.email or "",
            "password": test_password,
            "csrf_token": csrf_token,
        },
        follow_redirects=False,
    )
    if response.status_code not in [302, 303, 307]:
        raise RuntimeError(
            f"Login failed with status {response.status_code}: {response.text[:200]}"
        )
    return client


# Helper functions for tests


def login_user(client: TestClient, email: str, password: str) -> bool:
    """Helper to log in a user and return success status."""
    # Get CSRF token first
    login_page = client.get("/login")
    csrf_token_cookie = login_page.cookies.get("csrf_token")
    csrf_token = csrf_token_cookie if csrf_token_cookie is not None else ""

    response = client.post(
        "/login",
        data={"email": email, "password": password, "csrf_token": csrf_token},
        follow_redirects=False,
    )
    return response.status_code in [302, 303, 307]


def get_csrf_token(client: TestClient, url: str = "/") -> str:
    """Helper to extract CSRF token from a page."""
    response = client.get(url)
    # Extract CSRF token from cookies
    token = response.cookies.get("csrf_token")
    return token if token is not None else ""


def post_with_csrf(
    client: TestClient, url: str, data: Optional[Dict[str, Any]] = None, **kwargs: Any
) -> Any:
    """Helper to POST data with CSRF token automatically included.

    Args:
        client: TestClient instance
        url: URL to POST to
        data: Form data dictionary (optional, defaults to empty dict)
        **kwargs: Additional arguments to pass to client.post()

    Returns:
        Response from the POST request
    """
    # Get CSRF token
    csrf_token = get_csrf_token(client, url)

    # Add CSRF token to data
    data_with_csrf: Dict[str, Any] = {**(data or {}), "csrf_token": csrf_token}

    # Make the POST request
    return client.post(url, data=data_with_csrf, **kwargs)
