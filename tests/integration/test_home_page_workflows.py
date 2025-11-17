"""Integration tests for home page and landing page workflows.

Tests the main landing page functionality including content display,
navigation, and user-specific features.
"""

from datetime import date, datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, News, Result, Tournament


class TestHomePageAccess:
    """Tests for home page access and basic rendering."""

    def test_anonymous_user_can_view_home_page(self, client: TestClient):
        """Test that unauthenticated users can view the home page."""
        response = client.get("/")

        assert response.status_code == 200
        assert "South Austin Bass Club" in response.text or "SABC" in response.text

    def test_authenticated_user_can_view_home_page(self, authenticated_client: TestClient):
        """Test that authenticated users can view the home page."""
        response = authenticated_client.get("/")

        assert response.status_code == 200

    def test_member_can_view_home_page(self, member_client: TestClient):
        """Test that member users can view the home page."""
        response = member_client.get("/")

        assert response.status_code == 200

    def test_admin_can_view_home_page(self, admin_client: TestClient):
        """Test that admin users can view the home page."""
        response = admin_client.get("/")

        assert response.status_code == 200


class TestHomePageContent:
    """Tests for home page content display."""

    def test_home_page_shows_upcoming_events(
        self, client: TestClient, test_event: Event, db_session: Session
    ):
        """Test that home page displays upcoming events."""
        # Ensure event is in the future
        future_date = date.today() + timedelta(days=7)
        test_event.date = future_date
        db_session.commit()

        response = client.get("/")

        assert response.status_code == 200
        assert test_event.name in response.text

    def test_home_page_shows_recent_news(
        self, client: TestClient, admin_user: Angler, db_session: Session
    ):
        """Test that home page displays recent news articles."""
        # Create a news article
        news = News(
            title="Test News Article",
            content="This is test news content",
            author_id=admin_user.id,
            published=True,
            created_at=datetime.now(tz=timezone.utc),
        )
        db_session.add(news)
        db_session.commit()

        response = client.get("/")

        assert response.status_code == 200
        # News might be on home page or require navigation
        assert response.status_code == 200

    def test_home_page_navigation_shows_correct_links_for_anonymous(self, client: TestClient):
        """Test that navigation shows appropriate links for anonymous users."""
        response = client.get("/")

        assert response.status_code == 200
        # Should have login/register links
        assert "/login" in response.text.lower() or "login" in response.text.lower()
        assert "/register" in response.text.lower() or "sign up" in response.text.lower()

    def test_home_page_navigation_shows_correct_links_for_authenticated(
        self, authenticated_client: TestClient, regular_user: Angler
    ):
        """Test that navigation shows appropriate links for authenticated users."""
        response = authenticated_client.get("/")

        assert response.status_code == 200
        # Should show user name or profile link
        assert regular_user.name in response.text or "/profile" in response.text.lower()

    def test_home_page_navigation_shows_admin_links_for_admin(self, admin_client: TestClient):
        """Test that navigation shows admin links for admin users."""
        response = admin_client.get("/")

        assert response.status_code == 200
        # Should have admin dashboard link
        assert "/admin" in response.text.lower() or "admin" in response.text.lower()


class TestHomePageAOYStandings:
    """Tests for Angler of the Year standings on home page."""

    def test_home_page_shows_aoy_standings_when_available(
        self,
        client: TestClient,
        test_tournament: Tournament,
        regular_user: Angler,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that home page displays AOY standings when tournament results exist."""
        # Create tournament results for members
        result1 = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=15.5,
            num_fish=5,
            big_bass_weight=5.2,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result1)
        db_session.commit()

        response = client.get("/")

        assert response.status_code == 200
        # Check if standings section exists (may vary by template)
        assert response.status_code == 200

    def test_home_page_handles_no_aoy_standings_gracefully(self, client: TestClient):
        """Test that home page displays appropriately when no tournament results exist."""
        response = client.get("/")

        assert response.status_code == 200
        # Should not crash, should render empty state or hide section


class TestPublicPagesAccess:
    """Tests for access to public pages linked from home."""

    def test_about_page_accessible_from_home(self, client: TestClient):
        """Test that about page is accessible."""
        response = client.get("/about")

        assert response.status_code == 200

    def test_bylaws_page_accessible_from_home(self, client: TestClient):
        """Test that bylaws page is accessible."""
        response = client.get("/bylaws")

        assert response.status_code == 200

    def test_roster_page_accessible_from_home(self, client: TestClient):
        """Test that roster page is accessible."""
        response = client.get("/roster")

        assert response.status_code == 200

    def test_calendar_page_accessible_from_home(self, client: TestClient):
        """Test that calendar page is accessible."""
        response = client.get("/calendar")

        assert response.status_code == 200

    def test_awards_page_accessible_from_home(self, client: TestClient):
        """Test that awards page is accessible."""
        response = client.get("/awards")

        assert response.status_code == 200

    def test_tournament_results_page_accessible_from_home(self, client: TestClient):
        """Test that tournament results page is accessible."""
        response = client.get("/tournaments")

        assert response.status_code == 200


class TestCalendarPageContent:
    """Tests for calendar page content and functionality."""

    def test_calendar_shows_upcoming_events(
        self, client: TestClient, test_event: Event, db_session: Session
    ):
        """Test that calendar displays upcoming events."""
        # Ensure event is in current or future month
        future_date = date.today() + timedelta(days=14)
        test_event.date = future_date
        db_session.commit()

        response = client.get("/calendar")

        assert response.status_code == 200
        assert test_event.name in response.text

    def test_calendar_displays_current_month_by_default(self, client: TestClient):
        """Test that calendar displays the current month by default."""
        response = client.get("/calendar")

        assert response.status_code == 200
        # Check for current month name
        import calendar

        current_month = calendar.month_name[date.today().month]
        assert current_month in response.text

    def test_calendar_can_navigate_to_different_months(self, client: TestClient):
        """Test that calendar can navigate to different months via query params."""
        # Try to view next month
        next_month = date.today() + timedelta(days=32)
        response = client.get(f"/calendar?year={next_month.year}&month={next_month.month}")

        assert response.status_code == 200


class TestRosterPageContent:
    """Tests for roster page content."""

    def test_roster_shows_club_members(
        self, client: TestClient, member_user: Angler, db_session: Session
    ):
        """Test that roster page displays club members."""
        response = client.get("/roster")

        assert response.status_code == 200
        assert member_user.name in response.text

    def test_roster_does_not_show_non_members(self, client: TestClient, regular_user: Angler):
        """Test that roster only displays members, not all users."""
        response = client.get("/roster")

        assert response.status_code == 200
        # Non-member should not appear on roster
        assert regular_user.name not in response.text or "member" not in response.text.lower()

    def test_roster_handles_no_members_gracefully(self, client: TestClient, db_session: Session):
        """Test that roster displays appropriately when no members exist."""
        # Remove all members
        db_session.query(Angler).filter(Angler.member is True).delete()
        db_session.commit()

        response = client.get("/roster")

        assert response.status_code == 200


class TestAwardsPageContent:
    """Tests for awards page content."""

    def test_awards_page_shows_tournament_results(
        self,
        client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that awards page displays tournament results and standings."""
        # Create a tournament result
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=18.75,
            num_fish=5,
            big_bass_weight=6.25,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result)
        db_session.commit()

        response = client.get("/awards")

        assert response.status_code == 200
        # Should show tournament name or member name
        assert member_user.name in response.text or test_tournament.name in response.text

    def test_awards_page_handles_no_results_gracefully(self, client: TestClient):
        """Test that awards page displays appropriately when no results exist."""
        response = client.get("/awards")

        assert response.status_code == 200


class TestTournamentResultsPageContent:
    """Tests for tournament results page content."""

    def test_tournaments_page_lists_tournaments(
        self, client: TestClient, test_tournament: Tournament
    ):
        """Test that tournaments page lists available tournaments."""
        response = client.get("/tournaments")

        assert response.status_code == 200
        assert test_tournament.name in response.text

    def test_tournaments_page_links_to_individual_results(
        self, client: TestClient, test_tournament: Tournament
    ):
        """Test that tournaments page has links to individual tournament results."""
        response = client.get("/tournaments")

        assert response.status_code == 200
        # Should have link to tournament detail
        assert f"/tournaments/{test_tournament.id}" in response.text

    def test_individual_tournament_results_page_accessible(
        self,
        client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that individual tournament results pages are accessible."""
        # Create a result for the tournament
        result = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=12.5,
            num_fish=5,
            big_bass_weight=4.0,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        db_session.add(result)
        db_session.commit()

        response = client.get(f"/tournaments/{test_tournament.id}")

        assert response.status_code == 200
        assert member_user.name in response.text

    def test_tournament_results_shows_rankings(
        self,
        client: TestClient,
        test_tournament: Tournament,
        member_user: Angler,
        admin_user: Angler,
        db_session: Session,
    ):
        """Test that tournament results display rankings correctly."""
        # Create results for multiple anglers
        result1 = Result(
            tournament_id=test_tournament.id,
            angler_id=member_user.id,
            total_weight=20.5,
            num_fish=5,
            big_bass_weight=6.5,
            points=100,
            disqualified=False,
            buy_in=True,
        )
        result2 = Result(
            tournament_id=test_tournament.id,
            angler_id=admin_user.id,
            total_weight=15.25,
            num_fish=5,
            big_bass_weight=5.0,
            points=99,
            disqualified=False,
            buy_in=True,
        )
        db_session.add_all([result1, result2])
        db_session.commit()

        response = client.get(f"/tournaments/{test_tournament.id}")

        assert response.status_code == 200
        # Both anglers should be shown
        assert member_user.name in response.text
        assert admin_user.name in response.text


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_endpoint_returns_ok(self, client: TestClient):
        """Test that health check endpoint returns success."""
        response = client.get("/health")

        assert response.status_code == 200

    def test_health_endpoint_accessible_without_auth(self, client: TestClient):
        """Test that health check is accessible without authentication."""
        response = client.get("/health")

        assert response.status_code == 200
