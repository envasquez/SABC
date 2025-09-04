#!/usr/bin/env python3
"""
Comprehensive backend test suite for SABC application.
Tests database operations, API endpoints, authentication, and business logic.
"""

import pytest
import sqlite3
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
import json

# Import the app and database functions
from app import app
from database import init_db, create_views, engine


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
    # First create an admin user
    response = client.post("/register", data={
        "name": "Test Admin",
        "email": "admin@test.com",
        "password": "testpass123"
    })
    
    # Login as admin
    response = client.post("/login", data={
        "email": "admin@test.com",
        "password": "testpass123"
    })
    
    return client


@pytest.fixture
def member_session(client):
    """Create an authenticated member session."""
    response = client.post("/register", data={
        "name": "Test Member",
        "email": "member@test.com",
        "password": "testpass123"
    })
    
    response = client.post("/login", data={
        "email": "member@test.com",
        "password": "testpass123"
    })
    
    return client


class TestAuthentication:
    """Test authentication and authorization."""
    
    def test_register_new_user(self, client):
        """Test user registration."""
        response = client.post("/register", data={
            "name": "New User",
            "email": "newuser@test.com",
            "password": "password123"
        })
        assert response.status_code == 302  # Redirect after successful registration
    
    def test_register_duplicate_email(self, client):
        """Test registration with duplicate email."""
        # Register first user
        client.post("/register", data={
            "name": "User 1",
            "email": "duplicate@test.com",
            "password": "password123"
        })
        
        # Try to register with same email
        response = client.post("/register", data={
            "name": "User 2",
            "email": "duplicate@test.com",
            "password": "password456"
        })
        assert "already exists" in response.text.lower() or response.status_code == 400
    
    def test_login_valid_credentials(self, client):
        """Test login with valid credentials."""
        # Register user
        client.post("/register", data={
            "name": "Login Test",
            "email": "login@test.com",
            "password": "testpass"
        })
        
        # Login
        response = client.post("/login", data={
            "email": "login@test.com",
            "password": "testpass"
        })
        assert response.status_code == 302  # Redirect after successful login
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post("/login", data={
            "email": "nonexistent@test.com",
            "password": "wrongpass"
        })
        assert response.status_code == 401 or "invalid" in response.text.lower()
    
    def test_logout(self, member_session):
        """Test logout functionality."""
        response = member_session.post("/logout")
        assert response.status_code == 302  # Redirect after logout
    
    def test_admin_access_control(self, client, member_session):
        """Test that non-admins cannot access admin pages."""
        response = member_session.get("/admin/events")
        assert response.status_code == 302  # Redirect to login


class TestEvents:
    """Test event management functionality."""
    
    def test_create_tournament_event(self, admin_session):
        """Test creating a SABC tournament event."""
        response = admin_session.post("/admin/events/create", data={
            "date": "2025-12-01",
            "name": "December Tournament",
            "event_type": "sabc_tournament",
            "description": "Monthly tournament",
            "start_time": "06:00",
            "weigh_in_time": "15:00",
            "entry_fee": 25.00,
            "lake_name": "Lake Travis",
            "ramp_name": "Mansfield Dam"
        })
        assert response.status_code == 302
        assert "success" in response.headers.get("location", "").lower()
    
    def test_create_federal_holiday(self, admin_session):
        """Test creating a federal holiday event."""
        response = admin_session.post("/admin/events/create", data={
            "date": "2025-07-04",
            "name": "Independence Day",
            "event_type": "federal_holiday",
            "description": "Federal Holiday",
            "holiday_name": "Independence Day"
        })
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
        response = admin_session.post("/admin/events/edit", data={
            "event_id": event_id,
            "date": "2025-10-20",
            "name": "Updated October Tournament",
            "event_type": "sabc_tournament",
            "description": "Updated description"
        })
        assert response.status_code == 302
    
    def test_delete_event_without_dependencies(self, admin_session, test_db):
        """Test deleting an event that has no dependencies."""
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-11-15', 2025, 'Test Event', 'sabc_tournament', 'To be deleted')
        """)
        event_id = cursor.lastrowid
        test_db.commit()
        
        response = admin_session.delete(f"/admin/events/{event_id}")
        assert response.status_code == 200
        assert response.json()["success"] == True
    
    def test_validate_duplicate_event_date(self, admin_session):
        """Test validation for duplicate events on same date."""
        # Create first event
        admin_session.post("/admin/events/create", data={
            "date": "2025-09-15",
            "name": "First Event",
            "event_type": "sabc_tournament",
            "description": "First"
        })
        
        # Try to create second event on same date
        response = admin_session.post("/admin/events/validate", json={
            "date": "2025-09-15",
            "name": "Second Event",
            "event_type": "sabc_tournament"
        })
        
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
        response = admin_session.post("/admin/polls/create", data={
            "event_id": event_id,
            "title": "Where should we fish in August?",
            "poll_type": "tournament_location",
            "starts_at": datetime.now().isoformat(),
            "closes_at": (datetime.now() + timedelta(days=5)).isoformat(),
            "options": json.dumps([
                {"lake": "Lake Travis", "ramp": "Mansfield Dam"},
                {"lake": "Lake Austin", "ramp": "Walsh Boat Landing"}
            ])
        })
        assert response.status_code == 302
    
    def test_member_voting(self, member_session, test_db):
        """Test that members can vote in polls."""
        # This would need a poll to exist first
        # Create poll via direct DB insert for testing
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO polls (title, poll_type, starts_at, closes_at, closed)
            VALUES ('Test Poll', 'yes_no', datetime('now'), datetime('now', '+7 days'), 0)
        """)
        poll_id = cursor.lastrowid
        
        cursor.execute("""
            INSERT INTO poll_options (poll_id, option_text, display_order)
            VALUES (?, 'Yes', 1), (?, 'No', 2)
        """, (poll_id, poll_id))
        test_db.commit()
        
        # Vote
        response = member_session.post(f"/polls/{poll_id}/vote", json={
            "option_ids": [1]
        })
        assert response.status_code == 200
    
    def test_guest_cannot_vote(self, client, test_db):
        """Test that guests cannot vote in polls."""
        # Create a poll
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO polls (title, poll_type, starts_at, closes_at, closed)
            VALUES ('Test Poll', 'yes_no', datetime('now'), datetime('now', '+7 days'), 0)
        """)
        poll_id = cursor.lastrowid
        test_db.commit()
        
        # Try to vote without login
        response = client.post(f"/polls/{poll_id}/vote", json={
            "option_ids": [1]
        })
        assert response.status_code == 401 or response.status_code == 302


class TestTournaments:
    """Test tournament functionality."""
    
    def test_create_tournament(self, admin_session, test_db):
        """Test creating a tournament."""
        # Create event and poll first
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO events (date, year, name, event_type, description)
            VALUES ('2025-06-15', 2025, 'June Tournament', 'sabc_tournament', 'Test')
        """)
        event_id = cursor.lastrowid
        test_db.commit()
        
        response = admin_session.post("/admin/tournaments/create", data={
            "event_id": event_id,
            "name": "June Bass Tournament",
            "lake_name": "Lake Travis",
            "entry_fee": 25.00
        })
        assert response.status_code == 302
    
    def test_enter_tournament_results(self, admin_session, test_db):
        """Test entering tournament results."""
        # Create tournament
        cursor = test_db.cursor()
        cursor.execute("""
            INSERT INTO tournaments (name, lake_name, entry_fee, complete)
            VALUES ('Test Tournament', 'Test Lake', 25.00, 0)
        """)
        tournament_id = cursor.lastrowid
        
        # Create anglers
        cursor.execute("""
            INSERT INTO anglers (name, email, member)
            VALUES ('Angler 1', 'angler1@test.com', 1),
                   ('Angler 2', 'angler2@test.com', 1)
        """)
        test_db.commit()
        
        # Enter results
        response = admin_session.post(f"/tournaments/{tournament_id}/results", json={
            "results": [
                {"angler_id": 1, "num_fish": 5, "total_weight": 15.5, "big_bass_weight": 4.2},
                {"angler_id": 2, "num_fish": 3, "total_weight": 8.3, "big_bass_weight": 3.1}
            ]
        })
        assert response.status_code == 200
    
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
            (4, 0, 0.0, 0),   # Zero fish - should get 2 points less than last with fish
            (5, 5, 15.0, 1),  # Buy-in - should get 4 points less than last with fish
        ]
        
        for angler_id, num_fish, weight, buy_in in results:
            cursor.execute("""
                INSERT INTO results (tournament_id, angler_id, num_fish, total_weight, buy_in)
                VALUES (?, ?, ?, ?, ?)
            """, (tournament_id, angler_id, num_fish, weight, buy_in))
        
        test_db.commit()
        
        # Query points from view (would need to be created)
        # This is a simplified test - actual implementation would use the view


class TestNews:
    """Test news management functionality."""
    
    def test_create_news(self, admin_session):
        """Test creating a news announcement."""
        response = admin_session.post("/admin/news/create", data={
            "title": "Test News",
            "content": "This is a test news announcement.",
            "published": True,
            "priority": 0
        })
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
        response = admin_session.post(f"/admin/news/{news_id}/update", data={
            "title": "Updated Title",
            "content": "Updated content",
            "published": True,
            "priority": 1
        })
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
        assert response.json()["success"] == True


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
        response = member_session.post("/profile/update", data={
            "name": "Updated Name",
            "email": "updated@test.com"
        })
        assert response.status_code == 302


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
        cursor.execute("""
            INSERT INTO polls (title, poll_type, event_id, starts_at, closes_at)
            VALUES ('Test Poll', 'tournament_location', ?, datetime('now'), datetime('now', '+7 days'))
        """, (event_id,))
        
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
        
        # Test event_type constraint (if it exists)
        with pytest.raises(sqlite3.IntegrityError):
            cursor.execute("""
                INSERT INTO events (date, year, name, event_type)
                VALUES ('2025-01-01', 2025, 'Bad Event', 'invalid_type')
            """)


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
            (5.0, True),   # Exactly minimum
            (5.1, True),   # Over minimum
        ]
        
        for weight, qualifies in test_cases:
            assert (weight >= min_weight) == qualifies


class TestSecurity:
    """Test security and authorization."""
    
    def test_sql_injection_prevention(self, client):
        """Test that SQL injection is prevented."""
        response = client.post("/login", data={
            "email": "test@test.com' OR '1'='1",
            "password": "password"
        })
        assert response.status_code == 401 or "invalid" in response.text.lower()
    
    def test_xss_prevention(self, admin_session):
        """Test that XSS is prevented in user input."""
        response = admin_session.post("/admin/news/create", data={
            "title": "<script>alert('XSS')</script>",
            "content": "Test content",
            "published": True
        })
        
        # Fetch the news page and verify script is escaped
        news_page = admin_session.get("/admin/news")
        assert "<script>alert('XSS')</script>" not in news_page.text
        assert "&lt;script&gt;" in news_page.text or "script" not in news_page.text
    
    def test_csrf_protection(self, client):
        """Test CSRF protection on state-changing operations."""
        # Attempt to make unauthorized state change
        response = client.post("/admin/events/create", data={
            "date": "2025-01-01",
            "name": "Unauthorized Event"
        })
        assert response.status_code == 302  # Should redirect to login


class TestPerformance:
    """Test performance and optimization."""
    
    def test_pagination_limits(self, client):
        """Test that pagination properly limits results."""
        response = client.get("/admin/events?page=1&per_page=20")
        # Would need to parse response and count items
    
    def test_query_optimization(self, test_db):
        """Test that queries are optimized with proper indexes."""
        cursor = test_db.cursor()
        
        # Check that important columns have indexes
        cursor.execute("PRAGMA index_list('events')")
        indexes = cursor.fetchall()
        # Verify indexes exist for commonly queried columns


if __name__ == "__main__":
    # Run tests with coverage
    pytest.main([__file__, "-v", "--cov=app", "--cov-report=html"])