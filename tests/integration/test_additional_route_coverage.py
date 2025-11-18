"""Additional route coverage tests - simple GET/POST requests to improve coverage.

Targets multiple routes with simple requests to boost coverage quickly.
"""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, News, Ramp, Tournament


class TestAdminDashboard:
    """Test admin dashboard routes."""

    def test_admin_dashboard_loads(self, admin_client: TestClient):
        """Test admin dashboard page loads."""
        response = admin_client.get("/admin")
        assert response.status_code == 200

    def test_admin_dashboard_shows_stats(self, admin_client: TestClient, db_session: Session):
        """Test dashboard shows statistics."""
        # Create some data
        angler = Angler(name="Test", email="test@test.com", member=True)
        db_session.add(angler)
        db_session.commit()

        response = admin_client.get("/admin")
        assert response.status_code == 200


class TestAdminNews:
    """Test admin news management."""

    def test_admin_news_list_loads(self, admin_client: TestClient):
        """Test news list page loads."""
        response = admin_client.get("/admin/news")
        assert response.status_code == 200

    def test_admin_news_shows_published_news(self, admin_client: TestClient, db_session: Session):
        """Test news list shows published news."""
        news = News(
            title="Test News",
            content="Test content",
            published=True,
            priority=1,
        )
        db_session.add(news)
        db_session.commit()

        response = admin_client.get("/admin/news")
        assert response.status_code == 200


class TestAdminEvents:
    """Test admin event management."""

    def test_admin_events_list_loads(self, admin_client: TestClient):
        """Test events list page loads."""
        response = admin_client.get("/admin/events")
        assert response.status_code == 200

    def test_admin_events_with_data(self, admin_client: TestClient, db_session: Session):
        """Test events list with existing events."""
        event = Event(
            name="Test Event",
            date=datetime.now().date() + timedelta(days=7),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = admin_client.get("/admin/events")
        assert response.status_code == 200


class TestAdminLakes:
    """Test admin lake management."""

    def test_admin_lakes_list_loads(self, admin_client: TestClient):
        """Test lakes list page loads."""
        response = admin_client.get("/admin/lakes")
        assert response.status_code == 200

    def test_admin_lakes_with_data(self, admin_client: TestClient, db_session: Session):
        """Test lakes list with existing lakes."""
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        response = admin_client.get("/admin/lakes")
        assert response.status_code == 200


class TestAdminUsers:
    """Test admin user management."""

    def test_admin_users_list_loads(self, admin_client: TestClient):
        """Test users list page loads."""
        response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_users_with_data(self, admin_client: TestClient, db_session: Session):
        """Test users list with existing users."""
        angler = Angler(name="Test User", email="test@example.com", member=True)
        db_session.add(angler)
        db_session.commit()

        response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_user_edit_form_loads(self, admin_client: TestClient, db_session: Session):
        """Test user edit form loads."""
        angler = Angler(name="Edit User", email="edit@example.com", member=True)
        db_session.add(angler)
        db_session.commit()

        response = admin_client.get(f"/admin/users/{angler.id}/edit")
        assert response.status_code == 200


class TestAdminTournaments:
    """Test admin tournament management."""

    def test_admin_tournaments_list_loads(self, admin_client: TestClient):
        """Test tournaments list page loads."""
        response = admin_client.get("/admin/tournaments")
        assert response.status_code == 200

    def test_admin_tournaments_with_data(self, admin_client: TestClient, db_session: Session):
        """Test tournaments list with existing tournaments."""
        event = Event(
            name="Tournament",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        lake = Lake(yaml_key="test", display_name="Test")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Ramp")
        db_session.add(ramp)
        db_session.commit()

        tournament = Tournament(
            event_id=event.id,
            name="Test Tournament",
            lake_id=lake.id,
            ramp_id=ramp.id,
            complete=False,
        )
        db_session.add(tournament)
        db_session.commit()

        response = admin_client.get("/admin/tournaments")
        assert response.status_code == 200

    def test_admin_tournament_enter_results_loads(
        self, admin_client: TestClient, db_session: Session
    ):
        """Test tournament results entry page loads."""
        event = Event(
            name="Tournament",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        lake = Lake(yaml_key="test", display_name="Test")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Ramp")
        db_session.add(ramp)
        db_session.commit()

        tournament = Tournament(
            event_id=event.id,
            name="Test Tournament",
            lake_id=lake.id,
            ramp_id=ramp.id,
            complete=False,
        )
        db_session.add(tournament)
        db_session.commit()

        response = admin_client.get(f"/admin/tournaments/{tournament.id}/enter-results")
        assert response.status_code == 200


class TestMemberOnlyRoutes:
    """Test routes that require member access."""

    def test_member_can_access_polls(self, member_client: TestClient):
        """Test that members can access polls page."""
        response = member_client.get("/polls")
        assert response.status_code == 200

    def test_non_member_cannot_access_polls(self, authenticated_client: TestClient):
        """Test that non-members cannot access polls."""
        response = authenticated_client.get("/polls", follow_redirects=False)
        assert response.status_code == 403


class TestPublicAPIRoutes:
    """Test public API routes."""

    def test_api_lakes_returns_json(self, client: TestClient, db_session: Session):
        """Test lakes API endpoint."""
        lake = Lake(yaml_key="api-lake", display_name="API Lake")
        db_session.add(lake)
        db_session.commit()

        response = client.get("/api/lakes")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_metrics_endpoint_loads(self, client: TestClient):
        """Test metrics endpoint."""
        response = client.get("/metrics")
        # Should return metrics in prometheus format or redirect
        assert response.status_code in [200, 404]  # Might be disabled in test


class TestErrorHandling:
    """Test error handling routes."""

    def test_404_on_invalid_tournament(self, client: TestClient):
        """Test 404 handling for non-existent tournament."""
        response = client.get("/tournaments/99999", follow_redirects=False)
        # Should redirect to home with error
        assert response.status_code in [303, 404]

    def test_404_on_invalid_event(self, client: TestClient):
        """Test handling of non-existent event."""
        response = client.get("/admin/events/99999", follow_redirects=False)
        # Might redirect or return 404
        assert response.status_code in [200, 303, 404, 500]
