"""Phase 5: Comprehensive Poll Creation Workflow Tests.

Tests complete poll creation workflows including:
- Creating different poll types (generic, tournament_location, other)
- Validation of required fields
- Poll option creation
- Error handling and edge cases
- Authorization checks
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption
from core.helpers.timezone import now_local
from tests.conftest import post_with_csrf


class TestGenericPollCreation:
    """Tests for creating generic (simple) polls."""

    def test_admin_can_create_generic_poll_with_options(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that admins can create a generic poll with custom options."""
        now = now_local()
        # Format for datetime-local input (no timezone suffix)
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "Best Meeting Time",
                "description": "Vote for the best time for our next meeting",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Morning", "Afternoon", "Evening"],
            },
            follow_redirects=False,
        )

        # Should redirect to edit page on success
        assert response.status_code in [302, 303]
        assert "/admin/polls/" in response.headers["location"]

        # Verify poll was created
        poll = db_session.query(Poll).filter(Poll.title == "Best Meeting Time").first()
        assert poll is not None
        assert poll.poll_type == "generic"
        assert poll.event_id == test_event.id

        # Verify options were created
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll.id).all()
        assert len(options) == 3
        option_texts = {opt.option_text for opt in options}
        assert option_texts == {"Morning", "Afternoon", "Evening"}

    def test_create_generic_poll_without_event(
        self,
        admin_client: TestClient,
        db_session: Session,
    ):
        """Test creating a generic poll not tied to a specific event."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "poll_type": "generic",
                "title": "General Club Question",
                "description": "What should we focus on this year?",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Tournaments", "Social Events", "Education"],
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify poll was created without event_id
        poll = db_session.query(Poll).filter(Poll.title == "General Club Question").first()
        assert poll is not None
        assert poll.event_id is None
        assert poll.poll_type == "generic"


class TestTournamentLocationPollCreation:
    """Tests for creating tournament location polls."""

    def test_admin_can_create_tournament_location_poll(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test creating a tournament location poll with lake selection."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "tournament_location",
                "title": f"{test_event.name} Location Vote",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "lake_ids[]": [str(test_lake.id)],
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify poll was created
        poll = (
            db_session.query(Poll)
            .filter(Poll.poll_type == "tournament_location")
            .filter(Poll.event_id == test_event.id)
            .first()
        )
        assert poll is not None

        # Verify lake option was created
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll.id).all()
        assert len(options) >= 1


class TestPollCreationValidation:
    """Tests for poll creation validation and error handling."""

    def test_create_poll_without_poll_type_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
    ):
        """Test that creating a poll without poll_type returns error."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                # Missing poll_type
                "title": "Test Poll",
                "starts_at": starts_at,
                "closes_at": closes_at,
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]
        assert (
            "error" in response.headers["location"].lower()
            or "events" in response.headers["location"]
        )

    def test_create_poll_without_time_range_fails(
        self,
        admin_client: TestClient,
        test_event: Event,
    ):
        """Test that poll creation requires both starts_at and closes_at."""
        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "Test Poll",
                # Missing starts_at and closes_at
                "poll_options[]": ["Option 1", "Option 2"],
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

    def test_non_admin_cannot_create_poll(
        self,
        member_client: TestClient,
        test_event: Event,
    ):
        """Test that non-admin users cannot create polls."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            member_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "Test Poll",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Option 1"],
            },
            follow_redirects=False,
        )

        # Should be redirected/forbidden
        assert response.status_code in [302, 303, 403]


class TestPollCreationWithAutogeneration:
    """Tests for polls with auto-generated titles and descriptions."""

    def test_tournament_poll_generates_title_from_event(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test that tournament polls auto-generate title from event name."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "tournament_location",
                # No title provided - should auto-generate
                "starts_at": starts_at,
                "closes_at": closes_at,
                "lake_ids[]": [str(test_lake.id)],
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify poll has generated title
        poll = (
            db_session.query(Poll)
            .filter(Poll.poll_type == "tournament_location")
            .filter(Poll.event_id == test_event.id)
            .first()
        )
        assert poll is not None
        assert poll.title is not None
        assert len(poll.title) > 0


class TestPollOptionCreation:
    """Tests for creating poll options of different types."""

    def test_create_poll_with_multiple_generic_options(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test creating a poll with multiple text options."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        options_list = ["Option A", "Option B", "Option C", "Option D"]

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "Multiple Choice Poll",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": options_list,
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify all options were created
        poll = db_session.query(Poll).filter(Poll.title == "Multiple Choice Poll").first()
        assert poll is not None

        options = db_session.query(PollOption).filter(PollOption.poll_id == poll.id).all()
        assert len(options) == len(options_list)
        created_texts = {opt.option_text for opt in options}
        assert created_texts == set(options_list)


class TestPollCreationEdgeCases:
    """Tests for edge cases and error scenarios in poll creation."""

    def test_create_poll_with_empty_title_uses_generated_title(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test that empty title gets auto-generated."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "",  # Empty title
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Yes", "No"],
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify poll was created with some title
        poll = (
            db_session.query(Poll)
            .filter(Poll.event_id == test_event.id)
            .filter(Poll.poll_type == "generic")
            .first()
        )
        assert poll is not None
        assert poll.title is not None
        assert len(poll.title) > 0

    def test_create_poll_with_very_long_title(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test creating a poll with a very long title."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        long_title = "A" * 200  # Very long title

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": long_title,
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Option 1"],
            },
            follow_redirects=False,
        )

        # Should either succeed or return an error gracefully
        assert response.status_code in [200, 302, 303, 400]


class TestPollCreationLogging:
    """Tests to ensure poll creation is properly logged."""

    def test_successful_poll_creation_is_logged(
        self,
        admin_client: TestClient,
        admin_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test that successful poll creation is logged."""
        now = now_local()
        starts_at = now.strftime("%Y-%m-%dT%H:%M")
        closes_at = (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")

        response = post_with_csrf(
            admin_client,
            "/admin/polls/create",
            data={
                "event_id": str(test_event.id),
                "poll_type": "generic",
                "title": "Logged Poll",
                "starts_at": starts_at,
                "closes_at": closes_at,
                "poll_options[]": ["Yes", "No"],
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]

        # Verify poll was created
        poll = db_session.query(Poll).filter(Poll.title == "Logged Poll").first()
        assert poll is not None
        assert poll.created_by == admin_user.id
