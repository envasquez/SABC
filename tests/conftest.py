"""
Pytest configuration and shared fixtures for SABC tests.
"""

import pytest
import tempfile
import shutil
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright

# Import app components
from app import app
from database import init_db, create_views


@pytest.fixture(scope="session")
def test_database():
    """Create a test database for the session."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    test_db_path = Path(temp_dir) / "test.db"
    
    # Initialize test database
    conn = sqlite3.connect(test_db_path)
    cursor = conn.cursor()
    
    # Run table creation from database.py
    from database import TABLE_DEFINITIONS
    
    for table_def in TABLE_DEFINITIONS:
        cursor.execute(f"CREATE TABLE IF NOT EXISTS {table_def}")
    
    # Add test data
    test_data = [
        # Test users
        """INSERT INTO anglers (id, name, email, password, member, is_admin, active) VALUES 
           (1, 'Admin User', 'admin@test.com', '$2b$12$test', 1, 1, 1),
           (2, 'Member User', 'member@test.com', '$2b$12$test', 1, 0, 1),
           (3, 'Guest User', 'guest@test.com', '$2b$12$test', 0, 0, 1)""",
        
        # Test events
        """INSERT INTO events (id, date, year, name, event_type, description) VALUES
           (1, '2025-06-15', 2025, 'June Tournament', 'sabc_tournament', 'Test tournament'),
           (2, '2025-07-04', 2025, 'Independence Day', 'federal_holiday', 'Federal holiday'),
           (3, '2025-08-15', 2025, 'August Tournament', 'sabc_tournament', 'Another tournament')""",
        
        # Test news
        """INSERT INTO news (id, title, content, author_id, published, priority) VALUES
           (1, 'Test News', 'Test content', 1, 1, 0),
           (2, 'Draft News', 'Draft content', 1, 0, 1)""",
    ]
    
    for sql in test_data:
        cursor.execute(sql)
    
    conn.commit()
    
    yield test_db_path
    
    # Cleanup
    conn.close()
    shutil.rmtree(temp_dir)


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def authenticated_client(client):
    """Authenticated test client."""
    # Login
    response = client.post("/login", data={
        "email": "member@test.com",
        "password": "testpass"
    })
    return client


@pytest.fixture
def admin_client(client):
    """Admin authenticated test client."""
    # Login as admin
    response = client.post("/login", data={
        "email": "admin@test.com", 
        "password": "adminpass"
    })
    return client


@pytest.fixture(scope="session")
def browser():
    """Playwright browser for frontend tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,  # Set to False for debugging
            args=['--disable-web-security', '--disable-features=VizDisplayCompositor']
        )
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    """Playwright page for frontend tests."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080},
        ignore_https_errors=True
    )
    page = context.new_page()
    
    # Set longer timeout for slow operations
    page.set_default_timeout(30000)
    
    yield page
    
    context.close()


@pytest.fixture
def authenticated_page(browser):
    """Authenticated Playwright page."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    
    # Login process
    page.goto("http://localhost:8000/login")
    page.fill('input[name="email"]', "member@test.com")
    page.fill('input[name="password"]', "testpass")
    page.click('button[type="submit"]')
    page.wait_for_url("http://localhost:8000/")
    
    yield page
    
    context.close()


@pytest.fixture
def admin_page(browser):
    """Admin authenticated Playwright page."""
    context = browser.new_context(
        viewport={"width": 1920, "height": 1080}
    )
    page = context.new_page()
    
    # Admin login
    page.goto("http://localhost:8000/login")
    page.fill('input[name="email"]', "admin@test.com")
    page.fill('input[name="password"]', "adminpass")
    page.click('button[type="submit"]')
    page.wait_for_url("http://localhost:8000/")
    
    yield page
    
    context.close()


# Test data factories
@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "date": "2025-12-01",
        "name": "Test Tournament",
        "event_type": "sabc_tournament", 
        "description": "Test tournament event",
        "start_time": "06:00",
        "weigh_in_time": "15:00",
        "entry_fee": 25.00,
        "lake_name": "Test Lake",
        "ramp_name": "Test Ramp"
    }


@pytest.fixture
def sample_news_data():
    """Sample news data for testing."""
    return {
        "title": "Test News Article",
        "content": "This is test news content.",
        "published": True,
        "priority": 0
    }


@pytest.fixture
def sample_poll_data():
    """Sample poll data for testing."""
    return {
        "title": "Test Poll",
        "poll_type": "tournament_location",
        "options": [
            {"lake": "Lake Travis", "ramp": "Mansfield Dam"},
            {"lake": "Lake Austin", "ramp": "Red Bud Isle"}
        ]
    }


# Custom markers
def pytest_configure(config):
    """Configure custom markers."""
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "frontend: mark test as frontend test")
    config.addinivalue_line("markers", "backend: mark test as backend test")
    config.addinivalue_line("markers", "auth: mark test as authentication related")
    config.addinivalue_line("markers", "database: mark test as database related")


# Hooks for test reporting
def pytest_runtest_makereport(item, call):
    """Generate detailed test reports."""
    if "incremental" in item.keywords:
        if call.excinfo is not None:
            item.parent._previousfailed = item


def pytest_runtest_setup(item):
    """Setup for incremental tests."""
    if "incremental" in item.keywords:
        previousfailed = getattr(item.parent, "_previousfailed", None)
        if previousfailed is not None:
            pytest.xfail("previous test failed ({})".format(previousfailed.name))


# Performance monitoring
@pytest.fixture(autouse=True)
def track_performance(request):
    """Track test performance automatically."""
    import time
    
    start_time = time.time()
    
    yield
    
    duration = time.time() - start_time
    if duration > 5.0:  # Log slow tests
        print(f"\n⚠️  Slow test: {request.node.name} took {duration:.2f}s")


# Database state management
@pytest.fixture(autouse=True)
def reset_database_state():
    """Reset database state between tests."""
    # This would reset the database to a known state
    # Implementation depends on your specific needs
    yield
    # Cleanup after test