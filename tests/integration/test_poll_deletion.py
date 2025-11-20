"""Phase 6: Poll Deletion and Error Handling Tests.

Tests poll deletion workflows including:
- Deleting polls without votes
- Handling polls with existing votes
- Authorization checks
- Error handling for non-existent polls
"""

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Poll, PollOption, PollVote
from core.helpers.timezone import now_local
from tests.conftest import post_with_csrf


class TestPollDeletion:
    """Tests for deleting polls."""

    def test_admin_can_delete_poll_without_votes(
        self,
        admin_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test that admins can delete polls that have no votes."""
        now = now_local()
        poll = Poll(
            title="Test Poll",
            poll_type="generic",
            created_by=admin_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
        )
        db_session.add(poll)
        db_session.commit()
        poll_id = poll.id

        response = admin_client.delete(f"/admin/polls/{poll_id}")

        assert response.status_code in [200, 302, 303]

        # Verify poll was deleted
        deleted = db_session.query(Poll).filter(Poll.id == poll_id).first()
        assert deleted is None

    def test_admin_can_delete_poll_with_votes(
        self,
        admin_client: TestClient,
        db_session: Session,
        admin_user: Angler,
        member_user: Angler,
    ):
        """Test that polls with votes CAN be deleted (cascade delete)."""
        now = now_local()
        poll = Poll(
            title="Poll With Votes",
            poll_type="generic",
            created_by=admin_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
        )
        db_session.add(poll)
        db_session.flush()

        option = PollOption(poll_id=poll.id, option_text="Option A")
        db_session.add(option)
        db_session.flush()

        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()
        poll_id = poll.id

        response = admin_client.delete(f"/admin/polls/{poll_id}")

        assert response.status_code == 200

        # Verify poll and votes were deleted
        db_session.expire_all()
        deleted = db_session.query(Poll).filter(Poll.id == poll_id).first()
        assert deleted is None

    def test_delete_poll_also_deletes_options(
        self,
        admin_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test that deleting a poll also deletes its options."""
        now = now_local()
        poll = Poll(
            title="Poll With Options",
            poll_type="generic",
            created_by=admin_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
        )
        db_session.add(poll)
        db_session.flush()

        option1 = PollOption(poll_id=poll.id, option_text="Option 1")
        option2 = PollOption(poll_id=poll.id, option_text="Option 2")
        db_session.add_all([option1, option2])
        db_session.commit()

        poll_id = poll.id
        option1_id = option1.id
        option2_id = option2.id

        response = admin_client.delete(f"/admin/polls/{poll_id}")

        assert response.status_code in [200, 302, 303]

        # Verify options were also deleted
        db_session.expire_all()
        deleted_options = (
            db_session.query(PollOption).filter(PollOption.id.in_([option1_id, option2_id])).all()
        )
        assert len(deleted_options) == 0

    def test_delete_nonexistent_poll_succeeds_silently(
        self,
        admin_client: TestClient,
    ):
        """Test that deleting a non-existent poll returns success (idempotent)."""
        response = admin_client.delete("/admin/polls/99999")

        # Route returns 200 even for non-existent polls (idempotent)
        assert response.status_code == 200

    def test_non_admin_cannot_delete_poll(
        self,
        member_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test that non-admin users cannot delete polls."""
        now = now_local()
        poll = Poll(
            title="Protected Poll",
            poll_type="generic",
            created_by=admin_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
        )
        db_session.add(poll)
        db_session.commit()

        response = member_client.delete(f"/admin/polls/{poll.id}", follow_redirects=False)

        assert response.status_code in [302, 303, 403]

        # Verify poll still exists
        still_exists = db_session.query(Poll).filter(Poll.id == poll.id).first()
        assert still_exists is not None


class TestPollEditErrorHandling:
    """Tests for error handling in poll editing."""

    def test_edit_poll_with_missing_title_returns_error(
        self,
        admin_client: TestClient,
        db_session: Session,
        admin_user: Angler,
    ):
        """Test that editing a poll without title returns error."""
        now = now_local()
        poll = Poll(
            title="Original Title",
            poll_type="generic",
            created_by=admin_user.id,
            starts_at=now - timedelta(days=1),
            closes_at=now + timedelta(days=7),
        )
        db_session.add(poll)
        db_session.commit()

        response = post_with_csrf(
            admin_client,
            f"/admin/polls/{poll.id}/edit",
            data={
                "title": "",  # Empty title
                "description": "Test description",
                "starts_at": now.strftime("%Y-%m-%dT%H:%M"),
                "closes_at": (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"),
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert "error" in response.headers["location"].lower()

    def test_edit_nonexistent_poll_returns_error(
        self,
        admin_client: TestClient,
    ):
        """Test that editing a non-existent poll returns error."""
        now = now_local()
        response = post_with_csrf(
            admin_client,
            "/admin/polls/99999/edit",
            data={
                "title": "Test",
                "starts_at": now.strftime("%Y-%m-%dT%H:%M"),
                "closes_at": (now + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M"),
            },
            follow_redirects=False,
        )

        assert response.status_code in [302, 303]
        assert (
            "error" in response.headers.get("location", "").lower()
            or "polls" in response.headers.get("location", "").lower()
        )
