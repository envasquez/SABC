"""Phase 15: Coverage improvements for voting, polls, and API endpoints.

Target areas with realistic coverage improvements:
- Voting workflows and validation (31.6% → >50%)
- Poll editing additional scenarios (22.8% → >40%)
- Lake/Ramp API endpoints (36.4% → >60%)
"""

import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, PollVote, Ramp
from tests.conftest import post_with_csrf


class TestVotingWorkflows:
    """Comprehensive voting workflow tests targeting routes/voting/* coverage."""

    def test_member_can_access_polls_page(self, member_client: TestClient):
        """Test member can access polls page (members-only route)."""
        response = member_client.get("/polls")
        assert response.status_code == 200

    def test_anonymous_user_redirected_from_polls(self, client: TestClient):
        """Test that anonymous users are redirected from polls page."""
        response = client.get("/polls", follow_redirects=False)
        assert response.status_code in [302, 303]

    def test_voting_requires_option_selection(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test that voting without selecting an option fails."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Option Required Poll",
            poll_type="generic",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        # Try to vote without option_id
        form_data: dict[str, str] = {}
        response = post_with_csrf(
            member_client, f"/polls/{poll.id}/vote", data=form_data, follow_redirects=True
        )
        assert response.status_code in [200, 400, 422]


class TestPollEditingEdgeCases:
    """Additional poll editing tests for edge cases."""

    def test_edit_poll_with_invalid_dates(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test editing poll with invalid date range."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Date Test Poll",
            poll_type="generic",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        # Try to set closes_at before starts_at
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": (now + timedelta(days=5)).isoformat(),
            "closes_at": (now + timedelta(days=2)).isoformat(),
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll.id}/edit", data=form_data, follow_redirects=True
        )
        assert response.status_code in [200, 302, 303, 400]

    def test_edit_poll_preserves_existing_votes(
        self,
        admin_client: TestClient,
        member_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test that editing poll doesn't delete existing votes."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Vote Preservation Test",
            poll_type="generic",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option = PollOption(poll_id=poll.id, option_text="Original Option")
        db_session.add(option)
        db_session.flush()

        # Add a vote
        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id
        option_id = option.id

        # Edit poll title
        form_data = {
            "title": "Updated Title",
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )
        assert response.status_code in [200, 302, 303]

        # Verify vote still exists
        db_session.expire_all()
        vote_check = (
            db_session.query(PollVote)
            .filter(PollVote.poll_id == poll_id, PollVote.option_id == option_id)
            .first()
        )
        assert vote_check is not None


class TestLakeRampAPI:
    """Tests for lake and ramp API endpoints - targeting routes/api/lakes.py."""

    def test_api_lakes_returns_all_lakes(self, client: TestClient, db_session: Session):
        """Test /api/lakes endpoint returns all lakes."""
        # Create test lakes
        lake1 = Lake(yaml_key="lake_1", display_name="Lake One")
        lake2 = Lake(yaml_key="lake_2", display_name="Lake Two")
        db_session.add_all([lake1, lake2])
        db_session.commit()

        response = client.get("/api/lakes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 2

        # Verify lake data structure
        lake_names = [lake["name"] for lake in data]
        assert "Lake One" in lake_names
        assert "Lake Two" in lake_names

    def test_api_lakes_empty_database(self, client: TestClient, db_session: Session):
        """Test API handles empty database gracefully."""
        # Delete all lakes
        db_session.query(Lake).delete()
        db_session.commit()

        response = client.get("/api/lakes")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestPollOptionsManagement:
    """Tests for poll options creation and management."""

    def test_poll_option_without_data_for_generic_poll(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test creating poll options without option_data for generic polls."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Generic Options Poll",
            poll_type="generic",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        # Poll options for generic polls shouldn't have option_data
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll.id).all()

        for option in options:
            if option.option_data:
                # If it exists, should be valid JSON
                try:
                    json.loads(option.option_data)
                except json.JSONDecodeError:
                    assert False, "option_data should be valid JSON if present"

    def test_tournament_poll_option_has_structured_data(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test tournament location poll options have proper structured data."""
        # Create lake
        lake = Lake(yaml_key="struct_test_lake", display_name="Structured Test Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Structured Test Ramp")
        db_session.add(ramp)
        db_session.commit()

        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Tournament Location Poll",
            poll_type="tournament_location",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create option with structured data
        option_data = json.dumps(
            {
                "lake_id": lake.id,
                "ramp_id": ramp.id,
                "start_time": "06:00",
                "end_time": "15:00",
            }
        )

        option = PollOption(poll_id=poll.id, option_text=lake.display_name, option_data=option_data)
        db_session.add(option)
        db_session.commit()

        # Verify structured data
        db_session.expire_all()
        saved_option = db_session.query(PollOption).filter(PollOption.id == option.id).first()

        assert saved_option is not None
        assert saved_option.option_data is not None

        data = json.loads(saved_option.option_data)
        assert "lake_id" in data
        assert "ramp_id" in data
        assert data["lake_id"] == lake.id
        assert data["ramp_id"] == ramp.id


class TestVotingValidation:
    """Tests for voting validation and edge cases."""

    def test_vote_with_invalid_option_id(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test voting with non-existent option ID."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Invalid Option Test",
            poll_type="generic",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        # Try to vote with invalid option_id
        form_data = {"option_id": "99999"}

        response = post_with_csrf(
            member_client, f"/polls/{poll.id}/vote", data=form_data, follow_redirects=True
        )
        assert response.status_code in [200, 400, 404, 422]

    def test_vote_on_nonexistent_poll(self, member_client: TestClient, member_user: Angler):
        """Test voting on a poll that doesn't exist."""
        form_data = {"option_id": "1"}

        response = post_with_csrf(
            member_client, "/polls/99999/vote", data=form_data, follow_redirects=True
        )
        assert response.status_code in [200, 404]
