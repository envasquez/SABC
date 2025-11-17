"""End-to-end integration tests for poll voting workflow.

This module tests the critical poll voting functionality from member perspective,
covering the workflow from viewing polls to casting votes.
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, PollVote, Ramp


class TestPollVotingEndToEnd:
    """End-to-end tests for complete poll voting workflow."""

    def test_member_can_view_active_polls(
        self, member_client: TestClient, test_poll: Poll, test_poll_option: PollOption
    ):
        """Test that members can view the polls list page with active polls."""
        response = member_client.get("/polls")

        assert response.status_code == 200
        assert "Test Poll" in response.text
        assert "Test Option" in response.text
        assert test_poll.description is not None
        assert test_poll.description in response.text

    def test_non_member_cannot_access_polls(self, authenticated_client: TestClient):
        """Test that non-members are blocked from accessing polls."""
        response = authenticated_client.get("/polls", follow_redirects=False)

        # Should get 403 Forbidden
        assert response.status_code == 403

    def test_member_can_cast_vote_on_simple_poll(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_poll: Poll,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that a member can successfully cast a vote on a simple poll."""
        # Cast vote
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Should redirect after successful vote
        assert response.status_code in [302, 303]

        # Verify vote was recorded in database
        vote = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == test_poll.id,
                PollVote.angler_id == member_user.id,
                PollVote.option_id == test_poll_option.id,
            )
            .first()
        )
        assert vote is not None
        assert vote.option_id == test_poll_option.id

    def test_member_cannot_vote_twice_on_same_poll(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_poll: Poll,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that members cannot vote multiple times on the same poll."""
        # Cast first vote
        member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Try to vote again
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify only one vote exists
        vote_count = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == test_poll.id,
                PollVote.angler_id == member_user.id,
            )
            .count()
        )
        assert vote_count == 1

    def test_member_cannot_vote_on_closed_poll(
        self,
        member_client: TestClient,
        member_user: Angler,
        db_session: Session,
        test_event: Event,
        admin_user: Angler,
    ):
        """Test that members cannot vote on polls that have closed."""
        # Create a closed poll
        now = datetime.now(tz=timezone.utc)
        closed_poll = Poll(
            title="Closed Poll",
            description="This poll is closed",
            poll_type="simple",
            event_id=test_event.id,
            created_by=admin_user.id,
            created_at=now - timedelta(days=10),
            starts_at=now - timedelta(days=10),
            closes_at=now - timedelta(days=1),  # Closed yesterday
            closed=True,
            multiple_votes=False,
        )
        db_session.add(closed_poll)
        db_session.commit()
        db_session.refresh(closed_poll)

        # Create option for closed poll
        option = PollOption(
            poll_id=closed_poll.id,
            option_text="Closed Option",
            option_data=None,
            display_order=0,
        )
        db_session.add(option)
        db_session.commit()
        db_session.refresh(option)

        # Try to vote on closed poll
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(closed_poll.id),
                "option_id": str(option.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify vote was NOT recorded
        vote_count = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == closed_poll.id,
                PollVote.angler_id == member_user.id,
            )
            .count()
        )
        assert vote_count == 0

    def test_member_cannot_vote_on_future_poll(
        self,
        member_client: TestClient,
        member_user: Angler,
        db_session: Session,
        test_event: Event,
        admin_user: Angler,
    ):
        """Test that members cannot vote on polls that haven't started yet."""
        # Create a future poll
        now = datetime.now(tz=timezone.utc)
        future_poll = Poll(
            title="Future Poll",
            description="This poll starts tomorrow",
            poll_type="simple",
            event_id=test_event.id,
            created_by=admin_user.id,
            created_at=now,
            starts_at=now + timedelta(days=1),  # Starts tomorrow
            closes_at=now + timedelta(days=8),
            closed=False,
            multiple_votes=False,
        )
        db_session.add(future_poll)
        db_session.commit()
        db_session.refresh(future_poll)

        # Create option
        option = PollOption(
            poll_id=future_poll.id,
            option_text="Future Option",
            option_data=None,
            display_order=0,
        )
        db_session.add(option)
        db_session.commit()
        db_session.refresh(option)

        # Try to vote on future poll
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(future_poll.id),
                "option_id": str(option.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify vote was NOT recorded
        vote_count = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == future_poll.id,
                PollVote.angler_id == member_user.id,
            )
            .count()
        )
        assert vote_count == 0


class TestTournamentLocationPollVoting:
    """Tests for tournament location poll voting."""

    def test_member_can_vote_on_tournament_location_poll(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_event: Event,
        admin_user: Angler,
        test_lake: Lake,
        test_ramp: Ramp,
        db_session: Session,
    ):
        """Test member can vote on tournament location polls."""
        # Create tournament location poll
        now = datetime.now(tz=timezone.utc)
        tournament_poll = Poll(
            title="Tournament Location Vote",
            description="Vote for next tournament location",
            poll_type="tournament_location",
            event_id=test_event.id,
            created_by=admin_user.id,
            created_at=now,
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            closed=False,
            multiple_votes=False,
        )
        db_session.add(tournament_poll)
        db_session.commit()
        db_session.refresh(tournament_poll)

        # Create tournament location option with structured data
        option_data = {
            "lake_id": test_lake.id,
            "ramp_id": test_ramp.id,
            "start_time": "06:00",
            "end_time": "15:00",
        }
        option = PollOption(
            poll_id=tournament_poll.id,
            option_text=f"{test_lake.display_name} - {test_ramp.name}",
            option_data=option_data,
            display_order=0,
        )
        db_session.add(option)
        db_session.commit()
        db_session.refresh(option)

        # Cast vote
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(tournament_poll.id),
                "option_id": str(option.id),
            },
            follow_redirects=False,
        )

        # Should redirect after successful vote
        assert response.status_code in [302, 303]

        # Verify vote was recorded
        vote = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == tournament_poll.id,
                PollVote.angler_id == member_user.id,
            )
            .first()
        )
        assert vote is not None
        assert vote.option_id == option.id


class TestPollVotingPermissions:
    """Tests for poll voting permissions and security."""

    def test_unauthenticated_user_cannot_vote(
        self, client: TestClient, test_poll: Poll, test_poll_option: PollOption
    ):
        """Test that unauthenticated users cannot vote."""
        response = client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Should redirect to login
        assert response.status_code in [302, 303]
        assert "/login" in response.headers.get("location", "").lower()

    def test_authenticated_non_member_cannot_vote(
        self, authenticated_client: TestClient, test_poll: Poll, test_poll_option: PollOption
    ):
        """Test that authenticated but non-member users cannot vote."""
        response = authenticated_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Should get forbidden
        assert response.status_code == 403

    def test_member_cannot_vote_with_invalid_option(
        self,
        member_client: TestClient,
        test_poll: Poll,
        db_session: Session,
    ):
        """Test that voting with an invalid option ID fails."""
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": "99999",  # Invalid option ID
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify no vote was recorded
        vote_count = db_session.query(PollVote).filter(PollVote.poll_id == test_poll.id).count()
        assert vote_count == 0

    def test_member_cannot_vote_with_invalid_poll(
        self,
        member_client: TestClient,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that voting with an invalid poll ID fails."""
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": "99999",  # Invalid poll ID
                "option_id": str(test_poll_option.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify no vote was recorded
        vote_count = db_session.query(PollVote).count()
        assert vote_count == 0


class TestAdminProxyVoting:
    """Tests for admin proxy voting functionality."""

    def test_admin_can_cast_proxy_vote_for_member(
        self,
        admin_client: TestClient,
        admin_user: Angler,
        member_user: Angler,
        test_poll: Poll,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that admins can cast votes on behalf of members."""
        # Admin casts vote for member
        response = admin_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
                "vote_as_angler_id": str(member_user.id),
            },
            follow_redirects=False,
        )

        # Should redirect after successful vote
        assert response.status_code in [302, 303]

        # Verify proxy vote was recorded with correct metadata
        vote = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == test_poll.id,
                PollVote.angler_id == member_user.id,
            )
            .first()
        )
        assert vote is not None
        assert vote.option_id == test_poll_option.id
        assert vote.cast_by_admin is True
        assert vote.cast_by_admin_id == admin_user.id

    def test_non_admin_cannot_cast_proxy_vote(
        self,
        member_client: TestClient,
        member_user: Angler,
        admin_user: Angler,
        test_poll: Poll,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that non-admin members cannot cast proxy votes."""
        # Member tries to cast vote for admin
        response = member_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
                "vote_as_angler_id": str(admin_user.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error or be ignored
        assert response.status_code in [302, 303]

        # Verify no proxy vote was recorded for admin
        vote = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == test_poll.id,
                PollVote.angler_id == admin_user.id,
            )
            .first()
        )
        # Either no vote or vote is for the member themselves
        if vote:
            assert vote.angler_id == member_user.id

    def test_admin_cannot_proxy_vote_for_non_member(
        self,
        admin_client: TestClient,
        regular_user: Angler,
        test_poll: Poll,
        test_poll_option: PollOption,
        db_session: Session,
    ):
        """Test that admins cannot cast proxy votes for non-members."""
        response = admin_client.post(
            "/vote-poll",
            data={
                "poll_id": str(test_poll.id),
                "option_id": str(test_poll_option.id),
                "vote_as_angler_id": str(regular_user.id),
            },
            follow_redirects=False,
        )

        # Should redirect with error
        assert response.status_code in [302, 303]

        # Verify no vote was recorded for non-member
        vote = (
            db_session.query(PollVote)
            .filter(
                PollVote.poll_id == test_poll.id,
                PollVote.angler_id == regular_user.id,
            )
            .first()
        )
        assert vote is None
