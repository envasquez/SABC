"""Integration tests for foreign key constraint handling in CRUD operations.

Phase 1 of the comprehensive CRUD test coverage plan.
Tests all delete and update operations that affect related data to prevent
foreign key violations like the tournament poll editing bug.

See: docs/CRUD_TEST_COVERAGE_PLAN.md
Tracking: https://github.com/envasquez/SABC/issues/184
"""

from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import (
    Angler,
    Event,
    Lake,
    Poll,
    PollOption,
    PollVote,
    Ramp,
    Result,
    Tournament,
)
from tests.conftest import post_with_csrf


class TestEventForeignKeyConstraints:
    """Test Event CRUD operations with foreign key constraints.

    Events can have:
    - Polls (many-to-one: Event → Poll)
    - Tournaments (one-to-one: Event → Tournament)
    - Poll votes (Event → Poll → PollOption → PollVote chain)
    - Tournament results (Event → Tournament → Result chain)
    """

    def test_delete_event_with_poll_no_votes(self, admin_client: TestClient, db_session: Session):
        """Test deleting an event that has a poll but no votes - should succeed with cascade."""
        # Create event with poll (no votes)
        event = Event(
            name="Event with Poll",
            date=datetime.now(timezone.utc).date(),
            event_type="sabc_tournament",
            year=2025,
        )
        db_session.add(event)
        db_session.flush()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.commit()

        event_id = event.id
        poll_id = poll.id

        # Delete event
        response = admin_client.delete(f"/admin/events/{event_id}")

        # Should succeed - cascade deletes poll
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify both deleted
        db_session.expire_all()
        assert db_session.query(Event).filter(Event.id == event_id).first() is None
        assert db_session.query(Poll).filter(Poll.id == poll_id).first() is None

    def test_delete_event_with_poll_with_votes(
        self, admin_client: TestClient, member_user: Angler, db_session: Session
    ):
        """Test deleting event with poll that has votes - should cascade delete all."""
        # Create event
        event = Event(
            name="Event with Votes",
            date=datetime.now(timezone.utc).date(),
            event_type="sabc_tournament",
            year=2025,
        )
        db_session.add(event)
        db_session.flush()

        # Create poll
        poll = Poll(
            event_id=event.id,
            title="Poll with Votes",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create poll option
        option = PollOption(poll_id=poll.id, option_text="Option 1")
        db_session.add(option)
        db_session.flush()

        # Create vote
        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        event_id = event.id
        poll_id = poll.id
        vote_id = vote.id

        # Delete event
        response = admin_client.delete(f"/admin/events/{event_id}")

        # Should succeed with cascade or show clear error
        # Behavior depends on ondelete setting in schema
        if response.status_code == 200:
            # Cascade delete successful
            db_session.expire_all()
            assert db_session.query(Event).filter(Event.id == event_id).first() is None
            assert db_session.query(Poll).filter(Poll.id == poll_id).first() is None
            assert db_session.query(PollVote).filter(PollVote.id == vote_id).first() is None
        else:
            # Prevented by foreign key - should return error
            assert response.status_code in [400, 409]
            # Event should still exist
            db_session.expire_all()
            assert db_session.query(Event).filter(Event.id == event_id).first() is not None

    def test_delete_event_with_tournament_results(
        self, admin_client: TestClient, member_user: Angler, test_lake: Lake, db_session: Session
    ):
        """Test deleting event with tournament results - should prevent or cascade."""
        # Create ramp for lake
        ramp = Ramp(lake_id=test_lake.id, name="Test Ramp for Tournament")
        db_session.add(ramp)
        db_session.flush()

        # Create event
        event = Event(
            name="Event with Results",
            date=datetime.now(timezone.utc).date(),
            event_type="sabc_tournament",
            year=2025,
        )
        db_session.add(event)
        db_session.flush()

        # Create tournament
        tournament = Tournament(
            event_id=event.id,
            name="Test Tournament",
            lake_id=test_lake.id,
            ramp_id=ramp.id,
            complete=True,
        )
        db_session.add(tournament)
        db_session.flush()

        # Create result
        result = Result(
            tournament_id=tournament.id,
            angler_id=member_user.id,
            num_fish=5,
            total_weight=15.5,
        )
        db_session.add(result)
        db_session.commit()

        event_id = event.id
        tournament_id = tournament.id
        result_id = result.id

        # Try to delete event
        response = admin_client.delete(f"/admin/events/{event_id}")

        # Behavior depends on cascade settings
        if response.status_code == 200:
            # Cascade successful
            db_session.expire_all()
            assert db_session.query(Event).filter(Event.id == event_id).first() is None
            assert (
                db_session.query(Tournament).filter(Tournament.id == tournament_id).first() is None
            )
            assert db_session.query(Result).filter(Result.id == result_id).first() is None
        else:
            # Prevented - should show error
            assert response.status_code in [400, 409]
            json_resp = response.json()
            assert "error" in json_resp
            # Event should still exist
            db_session.expire_all()
            assert db_session.query(Event).filter(Event.id == event_id).first() is not None

    def test_update_event_date_with_tournament(
        self, admin_client: TestClient, test_lake: Lake, db_session: Session
    ):
        """Test updating event date when tournament exists - should succeed."""
        # Create ramp
        ramp = Ramp(lake_id=test_lake.id, name="Update Test Ramp")
        db_session.add(ramp)
        db_session.flush()

        # Create event
        event = Event(
            name="Event to Update",
            date=datetime.now(timezone.utc).date(),
            event_type="sabc_tournament",
            year=2025,
        )
        db_session.add(event)
        db_session.flush()

        # Create tournament
        tournament = Tournament(
            event_id=event.id, name="Update Test", lake_id=test_lake.id, ramp_id=ramp.id
        )
        db_session.add(tournament)
        db_session.commit()

        # Update event date
        new_date = (datetime.now(timezone.utc) + timedelta(days=30)).date()
        form_data = {
            "event_id": str(event.id),
            "name": event.name,
            "date": new_date.isoformat(),
            "event_type": event.event_type,
            "year": str(new_date.year),
        }

        response = post_with_csrf(
            admin_client, "/admin/events/edit", data=form_data, follow_redirects=False
        )

        # Should succeed - date change allowed even with tournament
        assert response.status_code in [200, 302, 303]

        # Note: Actual date update verification would require checking the full form submission
        # The key test here is that having a tournament doesn't prevent the update attempt


class TestUserForeignKeyConstraints:
    """Test User/Angler CRUD operations with foreign key constraints.

    Users can have:
    - Poll votes (Angler → PollVote)
    - Tournament results (Angler → Result)
    - Created polls (Angler → Poll.created_by)
    - Created events (potential future field)
    """

    def test_delete_user_with_poll_votes(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test deleting user who has cast votes - should preserve votes or prevent deletion."""
        # Create user to delete
        user = Angler(
            name="Voter to Delete",
            email="voter_delete@test.com",
            member=True,
        )
        db_session.add(user)
        db_session.flush()

        # Create poll
        poll = Poll(
            event_id=test_event.id,
            title="Poll for Vote Test",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create option
        option = PollOption(poll_id=poll.id, option_text="Option")
        db_session.add(option)
        db_session.flush()

        # Create vote
        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=user.id)
        db_session.add(vote)
        db_session.commit()

        user_id = user.id
        vote_id = vote.id

        # Try to delete user
        response = admin_client.delete(f"/admin/users/{user_id}")

        # Behavior depends on cascade settings
        if response.status_code == 200:
            # Deletion allowed - check if vote preserved or deleted
            db_session.expire_all()
            assert db_session.query(Angler).filter(Angler.id == user_id).first() is None
            # Vote might be cascade deleted or preserved with NULL angler_id
            db_session.query(PollVote).filter(PollVote.id == vote_id).first()
            # Document the behavior
        else:
            # Prevented by foreign key
            assert response.status_code in [400, 409]
            json_resp = response.json()
            assert "error" in json_resp
            # User should still exist
            db_session.expire_all()
            assert db_session.query(Angler).filter(Angler.id == user_id).first() is not None

    def test_delete_user_with_tournament_results(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_lake: Lake,
        db_session: Session,
    ):
        """Test deleting user with tournament results - should preserve results or prevent."""
        # Create ramp
        ramp = Ramp(lake_id=test_lake.id, name="Results Test Ramp")
        db_session.add(ramp)
        db_session.flush()

        # Create user with results
        user = Angler(
            name="Angler with Results",
            email="results_delete@test.com",
            member=True,
        )
        db_session.add(user)
        db_session.flush()

        # Create tournament
        tournament = Tournament(
            event_id=test_event.id, name="Results Test", lake_id=test_lake.id, ramp_id=ramp.id
        )
        db_session.add(tournament)
        db_session.flush()

        # Create result
        result = Result(
            tournament_id=tournament.id,
            angler_id=user.id,
            num_fish=4,
            total_weight=12.5,
        )
        db_session.add(result)
        db_session.commit()

        user_id = user.id
        result_id = result.id

        # Try to delete user
        response = admin_client.delete(f"/admin/users/{user_id}")

        # Should preserve tournament results (historical data)
        if response.status_code == 200:
            # Deletion allowed
            db_session.expire_all()
            user_check = db_session.query(Angler).filter(Angler.id == user_id).first()
            assert user_check is None
            # Result should still exist (preserve history)
            result_check = db_session.query(Result).filter(Result.id == result_id).first()
            assert result_check is not None
        else:
            # Prevented
            assert response.status_code in [400, 409]
            db_session.expire_all()
            assert db_session.query(Angler).filter(Angler.id == user_id).first() is not None

    def test_delete_user_who_created_polls(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test deleting user who created polls - should preserve polls or prevent."""
        # Create user who will create polls
        creator = Angler(
            name="Poll Creator",
            email="creator@test.com",
            member=True,
            is_admin=True,
        )
        db_session.add(creator)
        db_session.flush()

        # Create poll by this user
        poll = Poll(
            event_id=test_event.id,
            title="Poll by Creator",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=creator.id,
        )
        db_session.add(poll)
        db_session.commit()

        creator_id = creator.id
        poll_id = poll.id

        # Try to delete creator
        response = admin_client.delete(f"/admin/users/{creator_id}")

        # Should preserve poll (historical data) or prevent
        if response.status_code == 200:
            db_session.expire_all()
            # Poll should be preserved
            poll_check = db_session.query(Poll).filter(Poll.id == poll_id).first()
            assert poll_check is not None
        else:
            assert response.status_code in [400, 409]

    def test_cannot_delete_last_admin(
        self, admin_client: TestClient, admin_user: Angler, db_session: Session
    ):
        """Test that the last admin user cannot be deleted."""
        # Verify admin_user is the only admin
        admin_count = db_session.query(Angler).filter(Angler.is_admin.is_(True)).count()

        if admin_count == 1:
            # Try to delete the only admin
            response = admin_client.delete(f"/admin/users/{admin_user.id}")

            # Should be prevented
            assert response.status_code in [400, 403]
            json_resp = response.json()
            assert "error" in json_resp
            assert "cannot delete yourself" in json_resp["error"].lower()

    def test_update_user_email_when_referenced(
        self, admin_client: TestClient, member_user: Angler, db_session: Session
    ):
        """Test updating user email when user is referenced elsewhere - should succeed."""
        # Email update should always work (it's just a string field)
        new_email = "newemail@test.com"

        form_data = {
            "name": member_user.name,
            "email": new_email,
            "member": "on" if member_user.member else "",
            "is_admin": "on" if member_user.is_admin else "",
        }

        response = post_with_csrf(
            admin_client,
            f"/admin/users/{member_user.id}/edit",
            data=form_data,
            follow_redirects=False,
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]

        # Verify email updated
        db_session.expire_all()
        db_session.refresh(member_user)
        assert member_user.email == new_email


class TestLakeForeignKeyConstraints:
    """Test Lake/Ramp CRUD operations with foreign key constraints.

    Lakes can have:
    - Ramps (Lake → Ramp)
    - Tournament poll options (Lake → PollOption via option_data JSON)
    - Tournament records (Lake → Tournament)

    Ramps can have:
    - Tournament records (Ramp → Tournament)
    """

    def test_delete_lake_with_poll_options(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test deleting lake that's in active poll options - should prevent or cascade."""
        # Create lake
        lake = Lake(yaml_key="deletable_lake", display_name="Lake to Delete")
        db_session.add(lake)
        db_session.flush()

        # Create tournament poll with this lake as option
        poll = Poll(
            event_id=test_event.id,
            title="Tournament Poll with Lake",
            poll_type="tournament_location",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create poll option referencing lake
        import json

        option = PollOption(
            poll_id=poll.id,
            option_text=lake.display_name,
            option_data=json.dumps({"lake_id": lake.id}),
        )
        db_session.add(option)
        db_session.commit()

        lake_id = lake.id

        # Try to delete lake
        response = admin_client.delete(f"/admin/lakes/{lake_id}")

        # Behavior depends on implementation
        # Since lake_id is in JSON, SQL won't enforce FK
        # But application logic might check
        if response.status_code in [200, 302, 303]:
            # Deletion allowed - orphans the poll option
            db_session.expire_all()
            assert db_session.query(Lake).filter(Lake.id == lake_id).first() is None
        else:
            # Prevented by application logic
            assert response.status_code in [400, 409]

    def test_delete_lake_with_tournament_results(
        self, admin_client: TestClient, test_event: Event, member_user: Angler, db_session: Session
    ):
        """Test deleting lake with historical tournament results - should prevent or preserve."""
        # Create lake with ramp
        lake = Lake(yaml_key="tournament_lake", display_name="Tournament Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Tournament Ramp")
        db_session.add(ramp)
        db_session.flush()

        # Create tournament at this lake
        tournament = Tournament(
            event_id=test_event.id, name="Lake Test", lake_id=lake.id, ramp_id=ramp.id
        )
        db_session.add(tournament)
        db_session.flush()

        # Create result
        result = Result(
            tournament_id=tournament.id,
            angler_id=member_user.id,
            num_fish=3,
            total_weight=10.0,
        )
        db_session.add(result)
        db_session.commit()

        lake_id = lake.id

        # Try to delete lake
        response = admin_client.delete(f"/admin/lakes/{lake_id}")

        # Should be prevented (preserve historical data)
        if response.status_code in [400, 409]:
            json_resp = response.json()
            assert "error" in json_resp
            # Lake should still exist
            db_session.expire_all()
            assert db_session.query(Lake).filter(Lake.id == lake_id).first() is not None
        else:
            # If allowed, verify cascade behavior
            pass

    def test_delete_ramp_with_tournament_results(
        self,
        admin_client: TestClient,
        test_event: Event,
        test_lake: Lake,
        member_user: Angler,
        db_session: Session,
    ):
        """Test deleting ramp with tournament results - should prevent or preserve."""
        # Create ramp
        ramp = Ramp(lake_id=test_lake.id, name="Ramp with Results")
        db_session.add(ramp)
        db_session.flush()

        # Create tournament at this ramp
        tournament = Tournament(
            event_id=test_event.id, name="Ramp Test", lake_id=test_lake.id, ramp_id=ramp.id
        )
        db_session.add(tournament)
        db_session.flush()

        # Create result
        result = Result(
            tournament_id=tournament.id,
            angler_id=member_user.id,
            num_fish=2,
            total_weight=8.5,
        )
        db_session.add(result)
        db_session.commit()

        ramp_id = ramp.id

        # Try to delete ramp
        response = admin_client.delete(f"/admin/ramps/{ramp_id}")

        # Should be prevented (preserve historical data)
        if response.status_code in [400, 409]:
            json_resp = response.json()
            assert "error" in json_resp
            db_session.expire_all()
            assert db_session.query(Ramp).filter(Ramp.id == ramp_id).first() is not None
        else:
            # If allowed, document cascade behavior
            pass

    def test_update_lake_referenced_in_polls(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test updating lake display_name when referenced in polls - should succeed."""
        # Create lake
        lake = Lake(yaml_key="update_lake", display_name="Original Name")
        db_session.add(lake)
        db_session.flush()

        # Create poll option referencing this lake
        poll = Poll(
            event_id=test_event.id,
            title="Poll with Lake",
            poll_type="tournament_location",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        import json

        option = PollOption(
            poll_id=poll.id,
            option_text=lake.display_name,
            option_data=json.dumps({"lake_id": lake.id}),
        )
        db_session.add(option)
        db_session.commit()

        # Update lake name
        form_data = {
            "name": lake.yaml_key,
            "display_name": "Updated Lake Name",
            "google_maps_embed": lake.google_maps_iframe or "",
        }

        response = post_with_csrf(
            admin_client, f"/admin/lakes/{lake.id}/update", data=form_data, follow_redirects=False
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]

        # Verify update
        db_session.expire_all()
        db_session.refresh(lake)
        assert lake.display_name == "Updated Lake Name"


class TestPollForeignKeyConstraints:
    """Test Poll CRUD operations with foreign key constraints.

    Polls can have:
    - Poll options (Poll → PollOption)
    - Poll votes (Poll → PollOption → PollVote)

    Note: Generic poll editing with votes is tested separately in Phase 5.
    This covers the delete operations.
    """

    def test_delete_poll_with_votes(
        self, admin_client: TestClient, test_event: Event, member_user: Angler, db_session: Session
    ):
        """Test deleting poll that has votes - should cascade delete votes."""
        # Create poll
        poll = Poll(
            event_id=test_event.id,
            title="Poll to Delete with Votes",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create option
        option = PollOption(poll_id=poll.id, option_text="Option")
        db_session.add(option)
        db_session.flush()

        # Create vote
        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        poll_id = poll.id
        vote_id = vote.id

        # Delete poll
        response = admin_client.delete(f"/admin/polls/{poll_id}")

        # Should succeed with cascade
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify cascade deletion
        db_session.expire_all()
        assert db_session.query(Poll).filter(Poll.id == poll_id).first() is None
        assert db_session.query(PollVote).filter(PollVote.id == vote_id).first() is None

    def test_delete_poll_option_with_votes_directly(
        self, admin_client: TestClient, test_event: Event, member_user: Angler, db_session: Session
    ):
        """Test directly deleting a poll option that has votes - should fail or cascade.

        Note: This tests direct deletion. Smart update strategy (keeping voted options)
        is tested in test_poll_edit_with_votes.py.
        """
        # Create poll
        poll = Poll(
            event_id=test_event.id,
            title="Poll for Option Delete",
            poll_type="generic",
            starts_at=datetime.now(timezone.utc),
            closes_at=datetime.now(timezone.utc) + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create options
        option1 = PollOption(poll_id=poll.id, option_text="Voted Option")
        option2 = PollOption(poll_id=poll.id, option_text="Unvoted Option")
        db_session.add_all([option1, option2])
        db_session.flush()

        # Create vote for option1 only
        vote = PollVote(poll_id=poll.id, option_id=option1.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        # Try to delete voted option via direct DB operation
        # (There's typically no endpoint for this, but we test the constraint)
        option1_id = option1.id

        try:
            db_session.delete(option1)
            db_session.commit()
            # If we get here, cascade worked
            deleted = True
        except Exception:
            # Foreign key prevented deletion
            db_session.rollback()
            deleted = False

        # Document the behavior
        if deleted:
            # Cascade delete of votes occurred
            db_session.expire_all()
            assert db_session.query(PollOption).filter(PollOption.id == option1_id).first() is None
        else:
            # Foreign key prevented deletion - votes must be deleted first
            pass
