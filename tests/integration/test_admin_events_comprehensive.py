"""Comprehensive admin event management tests."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Event
from tests.conftest import post_with_csrf


class TestAdminEvents:
    """Test admin event management."""

    def test_admin_events_list(self, admin_client: TestClient):
        """Test admin events list page."""
        response = admin_client.get("/admin/events")
        assert response.status_code == 200

    def test_admin_create_tournament_event(self, admin_client: TestClient, db_session: Session):
        """Test admin creates tournament event."""
        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "name": f"New Tournament {datetime.now().timestamp()}",
                "date": (datetime.now().date() + timedelta(days=30)).isoformat(),
                "event_type": "tournament",
                "description": "Test tournament",
            },
        )
        assert response.status_code in [200, 303]

    def test_admin_create_meeting_event(self, admin_client: TestClient, db_session: Session):
        """Test admin creates meeting event."""
        response = post_with_csrf(
            admin_client,
            "/admin/events/create",
            data={
                "name": f"Meeting {datetime.now().timestamp()}",
                "date": (datetime.now().date() + timedelta(days=15)).isoformat(),
                "event_type": "meeting",
                "description": "Club meeting",
            },
        )
        assert response.status_code in [200, 303]

    def test_admin_edit_event(self, admin_client: TestClient, db_session: Session):
        """Test admin edits event."""
        event = Event(
            name="Edit Me",
            date=datetime.now().date() + timedelta(days=20),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = admin_client.get(f"/admin/events/{event.id}/edit")
        assert response.status_code == 200

    def test_admin_update_event(self, admin_client: TestClient, db_session: Session):
        """Test admin updates event."""
        event = Event(
            name="Update Me",
            date=datetime.now().date() + timedelta(days=25),
            year=datetime.now().year,
            event_type="social",
        )
        db_session.add(event)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/admin/events/{event.id}/update",
            data={
                "name": "Updated Event",
                "date": event.date.isoformat(),
                "event_type": "social",
                "description": "Updated",
            },
        )
        assert response.status_code in [200, 303]

    def test_admin_delete_event(self, admin_client: TestClient, db_session: Session):
        """Test admin deletes event."""
        event = Event(
            name="Delete Me",
            date=datetime.now().date() + timedelta(days=100),
            year=datetime.now().year,
            event_type="meeting",
        )
        db_session.add(event)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/admin/events/{event.id}/delete",
            data={},
        )
        assert response.status_code in [200, 303]
