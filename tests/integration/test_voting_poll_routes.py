"""Integration tests for voting and poll routes."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Event, Poll
from core.helpers.timezone import now_local


class TestPollListRoute:
    """Test poll listing route."""

    def test_polls_list_for_member(self, member_client: TestClient):
        """Test member can access polls list."""
        response = member_client.get("/polls")
        assert response.status_code == 200

    def test_polls_list_with_active_poll(
        self, member_client: TestClient, db_session: Session
    ):
        """Test polls list shows active polls."""
        event = Event(
            name="Event",
            date=datetime.now().date() + timedelta(days=7),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Active Poll",
            poll_type="simple",
            starts_at=now_local() - timedelta(hours=1),
            closes_at=now_local() + timedelta(days=1),
        )
        db_session.add(poll)
        db_session.commit()

        response = member_client.get("/polls")
        assert response.status_code == 200


class TestCreatePollRoute:
    """Test poll creation routes (admin only)."""

    def test_create_poll_form_loads_for_admin(self, admin_client: TestClient):
        """Test admin can load poll creation form."""
        response = admin_client.get("/admin/polls/create")
        assert response.status_code == 200


class TestPollHelpers:
    """Test poll helper functions."""

    def test_process_closed_polls(self):
        """Test closed polls processing."""
        from routes.voting.helpers import process_closed_polls

        # Should complete without error even with no polls
        process_closed_polls()
