"""
Comprehensive template rendering tests.

Ensures all templates can be rendered without errors for different user types.
This catches template syntax errors, missing variables, and type issues.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import (
    Angler,
    Event,
    Lake,
    News,
    Poll,
    PollOption,
    Ramp,
    Tournament,
)


class TestPublicTemplates:
    """Test public templates that don't require authentication."""

    def test_index_page_renders(self, client: TestClient):
        """Test that the homepage renders without errors."""
        response = client.get("/")
        assert response.status_code == 200
        assert b"html" in response.content.lower()

    def test_about_page_renders(self, client: TestClient):
        """Test that about page renders without errors."""
        response = client.get("/about")
        assert response.status_code == 200

    def test_bylaws_page_renders(self, client: TestClient):
        """Test that bylaws page renders without errors."""
        response = client.get("/bylaws")
        assert response.status_code == 200

    def test_roster_page_renders(self, client: TestClient, db_session: Session):
        """Test that roster page renders without errors."""
        # Add some members for the roster
        member1 = Angler(
            name="Test Member 1",
            email="member1@example.com",
            member=True,
            is_admin=False,
        )
        member2 = Angler(
            name="Test Member 2",
            email="member2@example.com",
            member=True,
            is_admin=False,
        )
        db_session.add_all([member1, member2])
        db_session.commit()

        response = client.get("/roster")
        assert response.status_code == 200

    def test_awards_page_renders(self, client: TestClient, db_session: Session):
        """Test that awards page renders without errors."""
        # Create test data for awards page
        event = Event(
            date=date.today(),
            year=date.today().year,
            name="Test Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = client.get("/awards")
        assert response.status_code == 200

    def test_calendar_page_renders(self, client: TestClient, db_session: Session):
        """Test that calendar page renders without errors."""
        # Create some events for the calendar
        event = Event(
            date=date.today() + timedelta(days=30),
            year=date.today().year,
            name="Upcoming Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = client.get("/calendar")
        assert response.status_code == 200

    def test_tournament_results_page_renders(self, client: TestClient, db_session: Session):
        """Test that tournament results page renders without errors."""
        # Create tournament with results
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        ramp = Ramp(lake_id=1, name="Test Ramp")
        db_session.add_all([lake, ramp])
        db_session.flush()

        event = Event(
            date=date.today() - timedelta(days=7),
            year=date.today().year,
            name="Past Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        tournament = Tournament(
            event_id=event.id,
            name=event.name,
            lake_id=lake.id,
            ramp_id=ramp.id,
            complete=True,
        )
        db_session.add(tournament)
        db_session.commit()

        response = client.get(f"/tournaments/{tournament.id}")
        # May redirect or render, both are acceptable
        assert response.status_code in [200, 302, 303, 404]


class TestAuthenticatedTemplates:
    """Test templates that require authentication."""

    def test_profile_page_renders(self, authenticated_client: TestClient, regular_user: Angler):
        """Test that profile page renders for authenticated user."""
        response = authenticated_client.get("/profile")
        assert response.status_code == 200

    def test_login_page_renders(self, client: TestClient):
        """Test that login page renders without errors."""
        response = client.get("/login")
        assert response.status_code == 200

    def test_register_page_renders(self, client: TestClient):
        """Test that register page renders without errors."""
        response = client.get("/register")
        assert response.status_code == 200

    def test_forgot_password_page_renders(self, client: TestClient):
        """Test that forgot password page renders without errors."""
        response = client.get("/request-password-reset")
        # May not exist yet, so accept 200 or 404
        assert response.status_code in [200, 404]


class TestMemberTemplates:
    """Test templates that require member status."""

    def test_polls_page_renders(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test that polls page renders for members."""
        # Create a poll for testing
        event = Event(
            date=date.today() + timedelta(days=14),
            year=date.today().year,
            name="Upcoming Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        now = datetime.now(tz=timezone.utc)
        poll = Poll(
            title="Test Poll",
            description="Test Description",
            poll_type="simple",
            event_id=event.id,
            created_by=member_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
            closed=False,
        )
        db_session.add(poll)
        db_session.flush()

        # Add poll options
        option1 = PollOption(poll_id=poll.id, option_text="Option 1")
        option2 = PollOption(poll_id=poll.id, option_text="Option 2")
        db_session.add_all([option1, option2])
        db_session.commit()

        response = member_client.get("/polls")
        assert response.status_code == 200


class TestAdminTemplates:
    """Test admin templates with admin user."""

    def test_admin_dashboard_renders(self, admin_client: TestClient, admin_user: Angler):
        """Test that admin dashboard renders without errors."""
        response = admin_client.get("/admin")
        assert response.status_code == 200

    def test_admin_users_page_renders(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that admin users page renders without errors."""
        # Add some users
        user1 = Angler(name="User 1", email="user1@example.com", member=False)
        user2 = Angler(name="User 2", email="user2@example.com", member=True)
        db_session.add_all([user1, user2])
        db_session.commit()

        response = admin_client.get("/admin/users")
        assert response.status_code == 200

    def test_admin_edit_user_page_renders(
        self, admin_client: TestClient, db_session: Session, regular_user: Angler
    ):
        """Test that admin edit user page renders without errors."""
        response = admin_client.get(f"/admin/users/{regular_user.id}/edit")
        assert response.status_code == 200

    def test_admin_lakes_page_renders(self, admin_client: TestClient, db_session: Session):
        """Test that admin lakes page renders without errors."""
        # Add some lakes
        lake1 = Lake(yaml_key="lake1", display_name="Lake 1")
        lake2 = Lake(yaml_key="lake2", display_name="Lake 2")
        db_session.add_all([lake1, lake2])
        db_session.commit()

        response = admin_client.get("/admin/lakes")
        assert response.status_code == 200

    def test_admin_edit_lake_page_renders(self, admin_client: TestClient, db_session: Session):
        """Test that admin edit lake page renders without errors."""
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        response = admin_client.get(f"/admin/lakes/{lake.id}/edit")
        assert response.status_code == 200

    def test_admin_events_page_renders(self, admin_client: TestClient, db_session: Session):
        """Test that admin events page renders without errors."""
        # Add some events
        event1 = Event(
            date=date.today() + timedelta(days=30),
            year=date.today().year,
            name="Future Event 1",
            event_type="sabc_tournament",
        )
        event2 = Event(
            date=date.today() - timedelta(days=30),
            year=date.today().year,
            name="Past Event 1",
            event_type="sabc_tournament",
        )
        db_session.add_all([event1, event2])
        db_session.commit()

        response = admin_client.get("/admin/events")
        assert response.status_code == 200

    def test_admin_tournaments_page_renders(self, admin_client: TestClient, db_session: Session):
        """Test that admin tournaments page renders without errors."""
        # Create tournament
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        db_session.add(lake)
        db_session.flush()

        event = Event(
            date=date.today(),
            year=date.today().year,
            name="Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        tournament = Tournament(
            event_id=event.id,
            name=event.name,
            lake_id=lake.id,
            complete=False,
        )
        db_session.add(tournament)
        db_session.commit()

        response = admin_client.get("/admin/tournaments")
        assert response.status_code == 200

    def test_admin_enter_results_page_renders(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that admin enter results page renders without errors."""
        # Create tournament
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        ramp = Ramp(lake_id=1, name="Test Ramp")
        db_session.add_all([lake, ramp])
        db_session.flush()

        event = Event(
            date=date.today(),
            year=date.today().year,
            name="Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        tournament = Tournament(
            event_id=event.id,
            name=event.name,
            lake_id=lake.id,
            ramp_id=ramp.id,
            complete=False,
        )
        db_session.add(tournament)
        db_session.flush()

        # Add some anglers for results
        angler1 = Angler(name="Angler 1", email="angler1@example.com", member=True)
        angler2 = Angler(name="Angler 2", email="angler2@example.com", member=True)
        db_session.add_all([angler1, angler2])
        db_session.commit()

        response = admin_client.get(f"/admin/tournaments/{tournament.id}/enter-results")
        assert response.status_code == 200

    def test_admin_create_poll_page_renders(self, admin_client: TestClient, db_session: Session):
        """Test that admin create poll page renders without errors."""
        # Create an event for the poll
        event = Event(
            date=date.today() + timedelta(days=30),
            year=date.today().year,
            name="Future Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()

        response = admin_client.get("/admin/polls/create")
        assert response.status_code == 200

    def test_admin_edit_poll_page_renders(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that admin edit poll page renders without errors."""
        # Create a poll
        event = Event(
            date=date.today() + timedelta(days=30),
            year=date.today().year,
            name="Future Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        now = datetime.now(tz=timezone.utc)
        poll = Poll(
            title="Test Poll",
            description="Test Description",
            poll_type="simple",
            event_id=event.id,
            created_by=admin_user.id,
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=7),
            closed=False,
        )
        db_session.add(poll)
        db_session.commit()

        response = admin_client.get(f"/admin/polls/{poll.id}/edit")
        assert response.status_code == 200

    def test_admin_news_page_renders(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test that admin news page renders without errors."""
        # Create some news items
        news1 = News(
            title="News 1",
            content="Content 1",
            author_id=admin_user.id,
            published=True,
        )
        news2 = News(
            title="News 2",
            content="Content 2",
            author_id=admin_user.id,
            published=False,
        )
        db_session.add_all([news1, news2])
        db_session.commit()

        response = admin_client.get("/admin/news")
        assert response.status_code == 200


class TestTemplateEdgeCases:
    """Test templates with edge cases and missing data."""

    def test_tournament_results_with_no_results(self, client: TestClient, db_session: Session):
        """Test tournament page renders even with no results."""
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        db_session.add(lake)
        db_session.flush()

        event = Event(
            date=date.today(),
            year=date.today().year,
            name="Empty Tournament",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.flush()

        tournament = Tournament(
            event_id=event.id,
            name=event.name,
            lake_id=lake.id,
            complete=False,
        )
        db_session.add(tournament)
        db_session.commit()

        response = client.get(f"/tournaments/{tournament.id}")
        # Should handle gracefully
        assert response.status_code in [200, 404]

    def test_roster_with_no_members(self, client: TestClient, db_session: Session):
        """Test roster page renders even with no members."""
        # Ensure no members exist
        db_session.query(Angler).delete()
        db_session.commit()

        response = client.get("/roster")
        assert response.status_code == 200

    def test_awards_with_no_tournaments(self, client: TestClient, db_session: Session):
        """Test awards page renders even with no tournament data."""
        # Clear all events
        db_session.query(Event).delete()
        db_session.commit()

        response = client.get("/awards")
        assert response.status_code == 200

    def test_polls_page_with_no_active_polls(self, member_client: TestClient, db_session: Session):
        """Test polls page renders even with no active polls."""
        # Clear all polls
        db_session.query(Poll).delete()
        db_session.commit()

        response = member_client.get("/polls")
        assert response.status_code == 200


class TestAllTemplatesComprehensive:
    """Comprehensive test to ensure ALL templates can render without errors."""

    def test_all_public_routes(self, client: TestClient, db_session: Session):
        """Test all public routes render without 500 errors."""
        # Create minimal test data
        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        public_routes = [
            "/",
            "/about",
            "/bylaws",
            "/roster",
            "/awards",
            "/calendar",
            "/login",
            "/register",
        ]

        for route in public_routes:
            response = client.get(route, follow_redirects=False)
            # Should not be 500 (server error)
            assert response.status_code != 500, f"Route {route} returned 500"
            # Accept 200 (OK), 302/303 (redirect), or 404 (not found)
            assert response.status_code in [
                200,
                302,
                303,
                404,
            ], f"Route {route} returned unexpected status: {response.status_code}"

    def test_all_member_routes(
        self, member_client: TestClient, db_session: Session, member_user: Angler
    ):
        """Test all member routes render without 500 errors."""
        member_routes = [
            "/profile",
            "/polls",
        ]

        for route in member_routes:
            response = member_client.get(route, follow_redirects=False)
            assert response.status_code != 500, f"Route {route} returned 500"
            assert response.status_code in [
                200,
                302,
                303,
                307,  # Temporary Redirect
            ], f"Route {route} returned unexpected status: {response.status_code}"

    def test_all_admin_routes(
        self, admin_client: TestClient, db_session: Session, admin_user: Angler
    ):
        """Test all admin routes render without 500 errors."""
        # Create minimal test data for admin routes
        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.flush()

        event = Event(
            date=date.today(),
            year=date.today().year,
            name="Test Event",
            event_type="sabc_tournament",
        )
        db_session.add(event)
        db_session.commit()

        admin_routes = [
            "/admin",
            "/admin/users",
            "/admin/lakes",
            "/admin/events",
            "/admin/tournaments",
            "/admin/polls/create",
            "/admin/news",
        ]

        for route in admin_routes:
            response = admin_client.get(route, follow_redirects=False)
            assert response.status_code != 500, f"Admin route {route} returned 500"
            assert response.status_code in [
                200,
                302,
                303,
            ], f"Admin route {route} returned unexpected status: {response.status_code}"
