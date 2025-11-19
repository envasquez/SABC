"""Integration tests for editing tournament polls with existing votes.

These tests cover the edge cases we fixed:
1. Editing tournament polls when they have existing votes
2. Foreign key constraint handling when removing lakes with votes
3. Smart update strategy for poll options
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, PollVote
from tests.conftest import post_with_csrf


class TestTournamentPollEditWithoutVotes:
    """Test editing tournament polls that have no votes."""

    def test_admin_can_edit_tournament_poll_lakes(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test changing lake selections when poll has no votes."""
        # Create lakes
        lake1 = Lake(yaml_key="lake_one", display_name="Lake One")
        lake2 = Lake(yaml_key="lake_two", display_name="Lake Two")
        lake3 = Lake(yaml_key="lake_three", display_name="Lake Three")
        db_session.add_all([lake1, lake2, lake3])
        db_session.flush()

        # Create tournament poll with lake1 and lake2
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Test Tournament Poll",
            description="Vote for lake",
            poll_type="tournament_location",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Add initial options for lake1 and lake2
        option1 = PollOption(
            poll_id=poll.id,
            option_text=lake1.display_name,
            option_data='{"lake_id": ' + str(lake1.id) + "}",
        )
        option2 = PollOption(
            poll_id=poll.id,
            option_text=lake2.display_name,
            option_data='{"lake_id": ' + str(lake2.id) + "}",
        )
        db_session.add_all([option1, option2])
        db_session.commit()

        poll_id = poll.id

        # Edit poll to remove lake2 and add lake3
        form_data = {
            "title": poll.title,
            "description": poll.description,
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "lake_ids": [str(lake1.id), str(lake3.id)],  # Remove lake2, add lake3
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code in [200, 302, 303]

        # Verify options updated correctly
        db_session.expire_all()
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
        option_lake_ids = []
        for opt in options:
            if opt.option_data:
                import json

                data = json.loads(opt.option_data)
                if "lake_id" in data:
                    option_lake_ids.append(data["lake_id"])

        # Should have lake1 and lake3, not lake2
        assert lake1.id in option_lake_ids
        assert lake3.id in option_lake_ids
        assert lake2.id not in option_lake_ids

    def test_admin_can_add_lakes_to_tournament_poll(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test adding new lakes to existing tournament poll."""
        # Create lakes
        lake1 = Lake(yaml_key="existing_lake", display_name="Existing Lake")
        lake2 = Lake(yaml_key="new_lake", display_name="New Lake")
        db_session.add_all([lake1, lake2])
        db_session.flush()

        # Create poll with only lake1
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Tournament Poll",
            poll_type="tournament_location",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option1 = PollOption(
            poll_id=poll.id,
            option_text=lake1.display_name,
            option_data='{"lake_id": ' + str(lake1.id) + "}",
        )
        db_session.add(option1)
        db_session.commit()

        poll_id = poll.id

        # Add lake2
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "lake_ids": [str(lake1.id), str(lake2.id)],
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code in [200, 302, 303]

        # Verify both lakes now in options
        db_session.expire_all()
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
        assert len(options) == 2


class TestTournamentPollEditWithVotes:
    """Test editing tournament polls that have existing votes - the critical edge case."""

    def test_admin_can_add_lakes_when_poll_has_votes(
        self,
        admin_client: TestClient,
        test_event: Event,
        member_user: Angler,
        db_session: Session,
    ):
        """Test adding new lakes to a poll that already has votes."""
        # Create lakes
        lake1 = Lake(yaml_key="voted_lake", display_name="Voted Lake")
        lake2 = Lake(yaml_key="new_addition", display_name="New Addition")
        db_session.add_all([lake1, lake2])
        db_session.flush()

        # Create poll
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Tournament with Votes",
            poll_type="tournament_location",
            starts_at=now - timedelta(hours=1),  # Already started
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Add option for lake1
        option1 = PollOption(
            poll_id=poll.id,
            option_text=lake1.display_name,
            option_data='{"lake_id": ' + str(lake1.id) + "}",
        )
        db_session.add(option1)
        db_session.flush()

        # Add vote for lake1
        vote = PollVote(poll_id=poll.id, option_id=option1.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id
        option1_id = option1.id

        # Add lake2 to poll (should succeed)
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "lake_ids": [str(lake1.id), str(lake2.id)],
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]
        assert "error" not in str(response.url).lower()

        # Verify lake1 option still exists (has votes)
        db_session.expire_all()
        option1_check = db_session.query(PollOption).filter(PollOption.id == option1_id).first()
        assert option1_check is not None

        # Verify lake2 option was added
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
        assert len(options) == 2

    def test_admin_cannot_remove_lake_with_votes(
        self,
        admin_client: TestClient,
        test_event: Event,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that lakes with votes are kept even when deselected."""
        # Create lakes
        lake1 = Lake(yaml_key="voted_lake_keep", display_name="Voted Lake")
        lake2 = Lake(yaml_key="unvoted_lake", display_name="Unvoted Lake")
        db_session.add_all([lake1, lake2])
        db_session.flush()

        # Create poll with both lakes
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Poll with Mixed Votes",
            poll_type="tournament_location",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option1 = PollOption(
            poll_id=poll.id,
            option_text=lake1.display_name,
            option_data='{"lake_id": ' + str(lake1.id) + "}",
        )
        option2 = PollOption(
            poll_id=poll.id,
            option_text=lake2.display_name,
            option_data='{"lake_id": ' + str(lake2.id) + "}",
        )
        db_session.add_all([option1, option2])
        db_session.flush()

        # Add vote only for lake1
        vote = PollVote(poll_id=poll.id, option_id=option1.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id
        option1_id = option1.id
        option2_id = option2.id

        # Try to remove both lakes (deselect all)
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "lake_ids": [],  # Deselect all - should fall back to all lakes
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        # Should succeed (falls back to all lakes when none selected)
        assert response.status_code in [200, 302, 303]

        # Try to remove just lake1 (which has votes)
        form_data["lake_ids"] = [str(lake2.id)]  # Only lake2, remove lake1

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        # Should succeed but lake1 should be kept
        assert response.status_code in [200, 302, 303]

        # Verify lake1 option still exists (has votes)
        db_session.expire_all()
        option1_check = db_session.query(PollOption).filter(PollOption.id == option1_id).first()
        assert option1_check is not None, "Lake with votes should not be deleted"

        # lake2 should still be there too
        option2_check = db_session.query(PollOption).filter(PollOption.id == option2_id).first()
        assert option2_check is not None

    def test_admin_can_remove_lake_without_votes(
        self,
        admin_client: TestClient,
        test_event: Event,
        member_user: Angler,
        db_session: Session,
    ):
        """Test that lakes WITHOUT votes can be removed successfully."""
        # Create lakes
        lake1 = Lake(yaml_key="voted_lake_1", display_name="Voted Lake")
        lake2 = Lake(yaml_key="unvoted_lake_2", display_name="Unvoted Lake")
        db_session.add_all([lake1, lake2])
        db_session.flush()

        # Create poll with both lakes
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Poll for Deletion Test",
            poll_type="tournament_location",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option1 = PollOption(
            poll_id=poll.id,
            option_text=lake1.display_name,
            option_data='{"lake_id": ' + str(lake1.id) + "}",
        )
        option2 = PollOption(
            poll_id=poll.id,
            option_text=lake2.display_name,
            option_data='{"lake_id": ' + str(lake2.id) + "}",
        )
        db_session.add_all([option1, option2])
        db_session.flush()

        # Add vote only for lake1
        vote = PollVote(poll_id=poll.id, option_id=option1.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id
        option2_id = option2.id

        # Remove lake2 (which has no votes)
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "lake_ids": [str(lake1.id)],  # Only keep lake1
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]

        # Verify lake2 option was deleted (no votes)
        db_session.expire_all()
        option2_check = db_session.query(PollOption).filter(PollOption.id == option2_id).first()
        assert option2_check is None, "Lake without votes should be deleted"

        # Verify only one option remains
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
        assert len(options) == 1


class TestPollEditEdgeCases:
    """Test edge cases and error conditions."""

    def test_edit_nonexistent_poll_returns_error(self, admin_client: TestClient):
        """Test editing a poll that doesn't exist."""
        form_data = {
            "title": "Ghost Poll",
            "description": "",
            "starts_at": datetime.now(timezone.utc).isoformat(),
            "closes_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        }

        response = post_with_csrf(
            admin_client, "/admin/polls/99999/edit", data=form_data, follow_redirects=True
        )

        # Should show error - 404 or redirect with error message
        assert response.status_code in [200, 404]
        if response.status_code == 200:
            # If 200, should have error message
            assert "error" in str(response.url).lower() or "not found" in response.text.lower()

    def test_non_admin_cannot_edit_poll(
        self, member_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test that non-admin users cannot edit polls."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Protected Poll",
            poll_type="generic",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        form_data = {
            "title": "Hacked Title",
            "description": "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
        }

        response = post_with_csrf(
            member_client, f"/admin/polls/{poll.id}/edit", data=form_data, follow_redirects=False
        )

        # Should deny access
        assert response.status_code in [302, 303, 403]
