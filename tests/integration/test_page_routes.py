"""Integration tests for public page routes."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event


class TestAwardsPage:
    """Test awards page."""

    def test_awards_page_loads(self, client: TestClient):
        """Test awards page loads."""
        response = client.get("/awards")
        assert response.status_code == 200

    def test_awards_with_year(self, client: TestClient):
        """Test awards page with year parameter."""
        response = client.get("/awards?year=2024")
        assert response.status_code == 200


class TestCalendarPage:
    """Test calendar page."""

    def test_calendar_page_loads(self, client: TestClient):
        """Test calendar page loads."""
        response = client.get("/calendar")
        assert response.status_code == 200

    def test_calendar_with_events(self, client: TestClient, db_session: Session):
        """Test calendar displays events."""
        event = Event(
            name="Future Event",
            date=datetime.now().date() + timedelta(days=30),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = client.get("/calendar")
        assert response.status_code == 200


class TestRosterPage:
    """Test roster page."""

    def test_roster_page_loads(self, client: TestClient):
        """Test roster page loads."""
        response = client.get("/roster")
        assert response.status_code == 200

    def test_roster_with_members(self, client: TestClient, db_session: Session):
        """Test roster displays members."""
        angler = Angler(name="Test Member", email="test@test.com", member=True)
        db_session.add(angler)
        db_session.commit()

        response = client.get("/roster")
        assert response.status_code == 200


class TestHealthCheck:
    """Test health check endpoint."""

    def test_health_endpoint(self, client: TestClient):
        """Test health check returns OK."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
