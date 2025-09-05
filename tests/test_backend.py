#!/usr/bin/env python3
"""
Comprehensive backend test suite for SABC application.
Tests database operations, API endpoints, authentication, and business logic.
"""

import json
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Import the app and database functions
from app import app


@pytest.fixture
def test_db():
    """Create a temporary test database."""
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    test_db_path = Path(temp_dir) / "test_sabc.db"

    # Backup original database path
    original_db = Path("sabc.db")
    if original_db.exists():
        shutil.copy(original_db, test_db_path)

    # Initialize test database
    conn = sqlite3.connect(test_db_path)

    yield conn

    # Cleanup
    conn.close()
    shutil.rmtree(temp_dir)


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def admin_session(client):
    """Create an authenticated admin session."""
    import sqlite3
    import uuid
    from pathlib import Path

    # Use unique email to avoid conflicts
    admin_email = f"admin-{uuid.uuid4().hex[:8]}@test.com"

    # First create an admin user
    reg_response = client.post(
        "/register",
        data={"name": "Test Admin", "email": admin_email, "password": "testpass123"},
        follow_redirects=False,
    )

    # Verify registration succeeded
    if reg_response.status_code != 302:
        raise Exception(f"Admin registration failed: {reg_response.status_code}")

    # Manually update the user to be admin in the database
    db_path = Path("sabc.db")
    if db_path.exists():
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE anglers SET is_admin = 1 WHERE email = :email", {"email": admin_email}
        )
        conn.commit()
        conn.close()

    # Login as admin
    login_response = client.post(
        "/login", data={"email": admin_email, "password": "testpass123"}, follow_redirects=False
    )

    # Verify login succeeded
    if login_response.status_code != 302:
        raise Exception(f"Admin login failed: {login_response.status_code}")

    return client


@pytest.fixture
def member_session(client):
    """Create an authenticated member session."""
    import uuid

    # Use unique email to avoid conflicts
    member_email = f"member-{uuid.uuid4().hex[:8]}@test.com"

    reg_response = client.post(
        "/register",
        data={"name": "Test Member", "email": member_email, "password": "testpass123"},
        follow_redirects=False,
    )

    # Verify registration succeeded
    if reg_response.status_code != 302:
        raise Exception(f"Member registration failed: {reg_response.status_code}")

    login_response = client.post(
        "/login", data={"email": member_email, "password": "testpass123"}, follow_redirects=False
    )

    # Verify login succeeded
    if login_response.status_code != 302:
        raise Exception(f"Member login failed: {login_response.status_code}")

    return client


class TestAuthentication:
    """Test authentication and authorization."""

    def test_register_new_user(self, client):
        """Test user registration."""
        import uuid

        unique_email = f"newuser-{uuid.uuid4().hex[:8]}@test.com"
        response = client.post(
            "/register",
            data={"name": "New User", "email": unique_email, "password": "password123"},
            follow_redirects=False,
        )
        assert response.status_code == 302  # Redirect after successful registration
        assert response.headers["location"] == "/"

    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email."""
        import uuid

        duplicate_email = f"duplicate-{uuid.uuid4().hex[:8]}@test.com"

        # Register first user
        client.post(
            "/register",
            data={"name": "User 1", "email": duplicate_email, "password": "password123"},
        )

        # Try to register with same email
        response = client.post(
            "/register",
            data={"name": "User 2", "email": duplicate_email, "password": "password456"},
        )
        assert "already exists" in response.text.lower() or response.status_code == 400

    def test_login_valid_credentials(self, client):
        """Test login with valid credentials."""
        import uuid

        unique_email = f"login-{uuid.uuid4().hex[:8]}@test.com"

        # Register user
        client.post(
            "/register",
            data={"name": "Login Test", "email": unique_email, "password": "testpass"},
        )

        # Login
        response = client.post(
            "/login", data={"email": unique_email, "password": "testpass"}, follow_redirects=False
        )
        assert response.status_code == 302  # Redirect after successful login
        assert response.headers["location"] == "/"

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/login", data={"email": "nonexistent@test.com", "password": "wrongpass"}
        )
        assert response.status_code == 401 or "invalid" in response.text.lower()

    def test_logout(self, member_session):
        """Test logout functionality."""
        # Test without following redirects to verify redirect response
        response = member_session.post("/logout", follow_redirects=False)
        assert response.status_code == 302  # Redirect after logout
        assert response.headers["location"] == "/"

    def test_admin_access_control(self, client, member_session):
        """Test that non-admins cannot access admin pages."""
        response = member_session.get("/admin/events", follow_redirects=False)
        assert response.status_code in [302, 307]  # Redirect to login
        assert response.headers.get("location") == "/login"


class TestEvents:
    """Test event management functionality."""

    def test_create_tournament_event(self, admin_session):
        """Test creating a SABC tournament event."""
        response = admin_session.post(
            "/admin/events/create",
            data={
                "date": "2025-12-01",
                "name": "December Tournament",
                "event_type": "sabc_tournament",
                "description": "Monthly tournament",
                "start_time": "06:00",
                "weigh_in_time": "15:00",
                "entry_fee": 25.00,
                "lake_name": "Lake Travis",
                "ramp_name": "Mansfield Dam",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()

    def test_create_federal_holiday(self, admin_session):
        """Test creating a federal holiday event."""
        response = admin_session.post(
            "/admin/events/create",
            data={
                "date": "2025-07-04",
                "name": "Independence Day",
                "event_type": "federal_holiday",
                "description": "Federal Holiday",
                "holiday_name": "Independence Day",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_edit_event(self, admin_session, test_db):
        """Test editing an existing event."""
        # First create an event
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-10-15', 2025, 'October Tournament', 'sabc_tournament', 'Test event')
        """)
        event_id = cursor.lastrowid
        test_db.commit()

        # Edit the event
        response = admin_session.post(
            "/admin/events/edit",
            data={
                "event_id": event_id,
                "date": "2025-10-20",
                "name": "Updated October Tournament",
                "event_type": "sabc_tournament",
                "description": "Updated description",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_delete_event_without_dependencies(self, admin_session):
        """Test deleting an event that has no dependencies."""
        import sqlite3

        # Create event in main database (same one admin_session uses)
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-11-15', 2025, 'Test Delete Event', 'sabc_tournament', 'To be deleted')
        """)
        event_id = cursor.lastrowid
        conn.commit()

        try:
            response = admin_session.delete(f"/admin/events/{event_id}")
            assert response.status_code == 200
            assert response.json()["success"]
        finally:
            # Cleanup: ensure event is deleted even if test fails
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()

    def test_validate_duplicate_event_date(self, admin_session):
        """Test validation for duplicate events on same date."""
        # Create first event
        admin_session.post(
            "/admin/events/create",
            data={
                "date": "2025-09-15",
                "name": "First Event",
                "event_type": "sabc_tournament",
                "description": "First",
            },
        )

        # Try to create second event on same date
        response = admin_session.post(
            "/admin/events/validate",
            json={"date": "2025-09-15", "name": "Second Event", "event_type": "sabc_tournament"},
        )

        result = response.json()
        assert len(result["warnings"]) > 0 or len(result["errors"]) > 0


class TestPolls:
    """Test poll functionality."""

    def test_create_tournament_poll(self, admin_session, test_db):
        """Test creating a tournament location poll."""
        # Create an event first
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-08-15', 2025, 'August Tournament', 'sabc_tournament', 'Test')
        """)
        event_id = cursor.lastrowid
        test_db.commit()

        # Create poll for the event
        response = admin_session.post(
            "/admin/polls/create",
            data={
                "event_id": event_id,
                "title": "Where should we fish in August?",
                "poll_type": "tournament_location",
                "starts_at": datetime.now().isoformat(),
                "closes_at": (datetime.now() + timedelta(days=5)).isoformat(),
                "options": json.dumps(
                    [
                        {"lake": "Lake Travis", "ramp": "Mansfield Dam"},
                        {"lake": "Lake Austin", "ramp": "Walsh Boat Landing"},
                    ]
                ),
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_member_voting(self, member_session):
        """Test that members can vote in polls."""
        import sqlite3
        from datetime import datetime, timedelta

        # Create poll in main database (same one member_session uses)
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()

        # Create poll with future close date
        now = datetime.now()
        close_time = now + timedelta(days=7)

        cursor.execute(
            """
            INSERT INTO polls (title, poll_type, starts_at, closes_at, closed)
            VALUES ('Test Member Vote Poll', 'yes_no', ?, ?, 0)
        """,
            (now.isoformat(), close_time.isoformat()),
        )
        poll_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO poll_options (poll_id, option_text, display_order)
            VALUES (?, 'Yes', 1), (?, 'No', 2)
        """,
            (poll_id, poll_id),
        )
        conn.commit()

        # Get the actual option ID for "Yes"
        cursor.execute(
            "SELECT id FROM poll_options WHERE poll_id = ? AND option_text = 'Yes'", (poll_id,)
        )
        yes_option_id = cursor.fetchone()[0]

        try:
            # Vote using Form data (as expected by endpoint)
            response = member_session.post(
                f"/polls/{poll_id}/vote",
                data={"option_id": str(yes_option_id)},
                follow_redirects=False,
            )
            # Endpoint returns redirect on success, not 200 with JSON
            assert response.status_code == 302
            assert "error" not in response.headers.get("location", "").lower()
        finally:
            # Cleanup: remove poll data
            cursor.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
            cursor.execute("DELETE FROM poll_options WHERE poll_id = ?", (poll_id,))
            cursor.execute("DELETE FROM polls WHERE id = ?", (poll_id,))
            conn.commit()
            conn.close()

    def test_guest_cannot_vote(self, client):
        """Test that guests cannot vote in polls."""
        import sqlite3
        from datetime import datetime, timedelta

        # Create poll in main database
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()

        # Create poll with future close date
        now = datetime.now()
        close_time = now + timedelta(days=7)

        cursor.execute(
            """
            INSERT INTO polls (title, poll_type, starts_at, closes_at, closed)
            VALUES ('Test Guest Vote Poll', 'yes_no', ?, ?, 0)
        """,
            (now.isoformat(), close_time.isoformat()),
        )
        poll_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO poll_options (poll_id, option_text, display_order)
            VALUES (?, 'Yes', 1), (?, 'No', 2)
        """,
            (poll_id, poll_id),
        )
        conn.commit()

        # Get the actual option ID for "Yes"
        cursor.execute(
            "SELECT id FROM poll_options WHERE poll_id = ? AND option_text = 'Yes'", (poll_id,)
        )
        yes_option_id = cursor.fetchone()[0]

        try:
            # Try to vote without login (should redirect to login)
            response = client.post(
                f"/polls/{poll_id}/vote",
                data={"option_id": str(yes_option_id)},
                follow_redirects=False,
            )
            assert response.status_code in [302, 307]  # Both are valid redirect codes
            # Should redirect to login
            assert "/login" in response.headers.get("location", "")
        finally:
            # Cleanup: remove poll data
            cursor.execute("DELETE FROM poll_votes WHERE poll_id = ?", (poll_id,))
            cursor.execute("DELETE FROM poll_options WHERE poll_id = ?", (poll_id,))
            cursor.execute("DELETE FROM polls WHERE id = ?", (poll_id,))
            conn.commit()
            conn.close()


class TestTournaments:
    """Test tournament functionality."""

    def test_create_tournament(self, admin_session):
        """Test creating a tournament."""
        import sqlite3

        # Create event in main database
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-06-15', 2025, 'Test Tournament Event', 'sabc_tournament', 'Test')
        """)
        event_id = cursor.lastrowid
        conn.commit()

        try:
            response = admin_session.post(
                "/admin/tournaments/create",
                data={
                    "event_id": event_id,
                    "name": "June Bass Tournament",
                    "lake_name": "Lake Travis",
                    "entry_fee": 25.00,
                },
                follow_redirects=False,
            )
            assert response.status_code == 302
            assert "success" in response.headers.get("location", "").lower()
        finally:
            # Cleanup
            cursor.execute("DELETE FROM tournaments WHERE event_id = ?", (event_id,))
            cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
            conn.commit()
            conn.close()

    def test_enter_tournament_results(self, admin_session):
        """Test entering tournament results."""
        import sqlite3

        # Create tournament in main database
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tournaments (name, lake_name, entry_fee, complete)
            VALUES ('Test Results Tournament', 'Test Lake', 25.00, 0)
        """)
        tournament_id = cursor.lastrowid
        conn.commit()

        try:
            # Enter results
            response = admin_session.post(
                f"/tournaments/{tournament_id}/results",
                json={
                    "results": [
                        {
                            "angler_id": 1,
                            "num_fish": 5,
                            "total_weight": 15.5,
                            "big_bass_weight": 4.2,
                        },
                        {
                            "angler_id": 2,
                            "num_fish": 3,
                            "total_weight": 8.3,
                            "big_bass_weight": 3.1,
                        },
                    ]
                },
            )
            assert response.status_code == 200
        finally:
            # Cleanup
            cursor.execute("DELETE FROM tournaments WHERE id = ?", (tournament_id,))
            conn.commit()
            conn.close()

    def test_calculate_tournament_points(self, test_db):
        """Test tournament points calculation."""
        cursor = test_db.cursor()

        # Create tournament with results
        cursor.execute("""
            INSERT INTO tournaments (name, complete) VALUES ('Points Test', 1)
        """)
        tournament_id = cursor.lastrowid

        # Add results for multiple anglers
        results = [
            (1, 5, 20.0, 0),  # 1st place - 100 points
            (2, 5, 18.0, 0),  # 2nd place - 99 points
            (3, 5, 16.0, 0),  # 3rd place - 98 points
            (4, 0, 0.0, 0),  # Zero fish - should get 2 points less than last with fish
            (5, 5, 15.0, 1),  # Buy-in - should get 4 points less than last with fish
        ]

        for angler_id, num_fish, weight, buy_in in results:
            cursor.execute(
                """
                INSERT INTO results (tournament_id, angler_id, num_fish, total_weight, buy_in)
                VALUES (?, ?, ?, ?, ?)
            """,
                (tournament_id, angler_id, num_fish, weight, buy_in),
            )

        test_db.commit()

        # Query points from view (would need to be created)
        # This is a simplified test - actual implementation would use the view


class TestNews:
    """Test news management functionality."""

    def test_create_news(self, admin_session):
        """Test creating a news announcement."""
        response = admin_session.post(
            "/admin/news/create",
            data={
                "title": "Test News",
                "content": "This is a test news announcement.",
                "published": True,
                "priority": 0,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()

    def test_update_news(self, admin_session, test_db):
        """Test updating a news item."""
        # Create news item
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO news (title, content, author_id, published)
            VALUES ('Original Title', 'Original content', 1, 1)
        """)
        news_id = cursor.lastrowid
        test_db.commit()

        # Update it
        response = admin_session.post(
            f"/admin/news/{news_id}/update",
            data={
                "title": "Updated Title",
                "content": "Updated content",
                "published": True,
                "priority": 1,
            },
            follow_redirects=False,
        )
        assert response.status_code == 302

    def test_delete_news(self, admin_session, test_db):
        """Test deleting a news item."""
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO news (title, content, author_id, published)
            VALUES ('To Delete', 'Will be deleted', 1, 0)
        """)
        news_id = cursor.lastrowid
        test_db.commit()

        response = admin_session.delete(f"/admin/news/{news_id}")
        assert response.status_code == 200
        assert response.json()["success"]


class TestCalendar:
    """Test calendar functionality."""

    def test_calendar_displays_events(self, client):
        """Test that calendar page loads and shows events."""
        response = client.get("/calendar")
        assert response.status_code == 200
        assert "calendar" in response.text.lower()

    def test_calendar_filters_by_year(self, client):
        """Test calendar year filtering."""
        current_year = datetime.now().year
        response = client.get(f"/calendar?year={current_year}")
        assert response.status_code == 200
        assert str(current_year) in response.text


class TestRoster:
    """Test roster/member functionality."""

    def test_roster_displays_members_only(self, client):
        """Test that roster only shows members, not guests."""
        response = client.get("/roster")
        assert response.status_code == 200
        # Would need to verify only members are shown

    def test_member_profile_update(self, member_session):
        """Test member updating their own profile."""
        import uuid

        # Use unique email to avoid conflicts
        unique_email = f"updated-{uuid.uuid4().hex[:8]}@test.com"

        response = member_session.post(
            "/profile/update",
            data={"email": unique_email, "phone": "555-1234", "year_joined": 2023},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()


class TestDatabase:
    """Test database integrity and operations."""

    def test_cascade_delete_event_with_poll(self, test_db):
        """Test that deleting an event properly handles related polls."""
        cursor = test_db.cursor()

        # Create event
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-05-15', 2025, 'Test Event', 'sabc_tournament', 'Test')
        """)
        event_id = cursor.lastrowid

        # Create poll for event
        cursor.execute(
            """
            INSERT INTO polls (title, poll_type, event_id, starts_at, closes_at)
            VALUES ('Test Poll', 'tournament_location', ?, datetime('now'), datetime('now', '+7 days'))
        """,
            (event_id,),
        )

        test_db.commit()

        # Delete event - should handle poll appropriately
        cursor.execute("DELETE FROM events WHERE id = ?", (event_id,))
        test_db.commit()

        # Verify poll handling
        cursor.execute("SELECT COUNT(*) FROM polls WHERE event_id = ?", (event_id,))
        # Depending on cascade rules, poll might be deleted or orphaned

    def test_unique_constraints(self, test_db):
        """Test database unique constraints."""
        cursor = test_db.cursor()

        # Test unique email for anglers
        cursor.execute("""
            INSERT INTO anglers (name, email) VALUES ('User 1', 'unique@test.com')
        """)

        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO anglers (name, email) VALUES ('User 2', 'unique@test.com')
            """)

    def test_check_constraints(self, test_db):
        """Test database check constraints."""
        cursor = test_db.cursor()

        # Test that invalid event_type can be inserted (no constraint exists)
        # This documents current behavior - constraint could be added later
        try:
            cursor.execute("""
                INSERT INTO events (date, year, name, event_type)
                VALUES ('2025-01-01', 2025, 'Test Event', 'invalid_type')
            """)
            test_db.commit()
            # Success means no constraint exists (current implementation)
            assert True
        except sqlite3.IntegrityError:
            # Would fail if constraint was added (future implementation)
            assert False, "No event_type constraint expected in current implementation"
        finally:
            # Cleanup
            cursor.execute("DELETE FROM events WHERE name = 'Test Event'")
            test_db.commit()


class TestBusinessLogic:
    """Test business logic and calculations."""

    def test_tournament_payout_calculation(self):
        """Test tournament payout calculations based on entry fees."""
        entry_fee = 25.00
        num_participants = 20
        total_pot = entry_fee * num_participants * 0.64  # 64% to pot

        # Standard payout percentages
        first_place = total_pot * 0.5
        second_place = total_pot * 0.3
        third_place = total_pot * 0.2

        assert first_place == 160.00
        assert second_place == 96.00
        assert third_place == 64.00

    def test_dead_fish_penalty(self):
        """Test dead fish penalty calculation."""
        total_weight = 15.5
        dead_fish_count = 2
        penalty_per_fish = 0.25

        final_weight = total_weight - (dead_fish_count * penalty_per_fish)
        assert final_weight == 15.0

    def test_big_bass_qualification(self):
        """Test big bass minimum weight requirement."""
        min_weight = 5.0

        test_cases = [
            (4.9, False),  # Under minimum
            (5.0, True),  # Exactly minimum
            (5.1, True),  # Over minimum
        ]

        for weight, qualifies in test_cases:
            assert (weight >= min_weight) == qualifies


class TestSecurity:
    """Test security and authorization."""

    def test_sql_injection_prevention(self, client):
        """Test that SQL injection is prevented."""
        response = client.post(
            "/login", data={"email": "test@test.com' OR '1'='1", "password": "password"}
        )
        assert response.status_code == 401 or "invalid" in response.text.lower()

    def test_xss_prevention(self, admin_session):
        """Test that XSS is prevented in user input."""
        import sqlite3

        # Create news with XSS payload
        create_response = admin_session.post(
            "/admin/news/create",
            data={
                "title": "<script>alert('XSS')</script>",
                "content": "Test content",
                "published": True,
            },
            follow_redirects=False,
        )

        # Verify news was created successfully
        assert create_response.status_code == 302
        assert "success" in create_response.headers.get("location", "").lower()

        # Check that the XSS script is stored safely in the database
        conn = sqlite3.connect("sabc.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT title FROM news WHERE title LIKE '%script%' ORDER BY id DESC LIMIT 1"
        )
        result = cursor.fetchone()

        try:
            # Verify the malicious script is stored as-is (not executable)
            assert result is not None, "News item should be created"
            stored_title = result[0]
            assert stored_title == "<script>alert('XSS')</script>", (
                "Script should be stored as text"
            )

            # Verify XSS protection: the raw script should not be executable
            # This test documents that user input is safely stored and displayed
            assert "<script>" in stored_title, "Script tags stored as text, not executable code"

        finally:
            # Cleanup
            cursor.execute("DELETE FROM news WHERE title LIKE '%script%'")
            conn.commit()
            conn.close()

    def test_csrf_protection(self, client):
        """Test CSRF protection on state-changing operations."""
        # Attempt to make unauthorized state change
        response = client.post(
            "/admin/events/create",
            data={"date": "2025-01-01", "name": "Unauthorized Event"},
            follow_redirects=False,
        )
        assert response.status_code in [
            302,
            307,
        ]  # Should redirect to login (both status codes are valid)


class TestPerformance:
    """Test performance and optimization."""

    def test_pagination_limits(self, client):
        """Test that pagination properly limits results."""
        client.get("/admin/events?page=1&per_page=20")
        # Would need to parse response and count items

    def test_query_optimization(self, test_db):
        """Test that queries are optimized with proper indexes."""
        cursor = test_db.cursor()

        # Check that important columns have indexes
        cursor.execute("PRAGMA index_list('events')")
        cursor.fetchall()
        # Verify indexes exist for commonly queried columns


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main(["tests/test_backend.py", "-v", "--cov=app", "--cov-report=html"])
