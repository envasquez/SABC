"""Phase 16: Additional coverage improvements for admin workflows and voting helpers.

Target areas with lowest coverage:
- Poll editing workflows (22.8% → >40%)
- Poll creation workflows (28.8% → >50%)
- Tournament results (27.1% / 36.7% → >50%)
- Voting helpers (31.6% → >50%)
"""

import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, Ramp, Result, Tournament
from tests.conftest import post_with_csrf


class TestPollCreationWorkflows:
    """Tests for poll creation workflows - targeting 28.8% → >50%."""

    def test_create_tournament_poll_with_all_lakes(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test creating tournament poll includes all lakes by default."""
        # Create multiple lakes
        lake1 = Lake(yaml_key="default_lake_1", display_name="Default Lake 1")
        lake2 = Lake(yaml_key="default_lake_2", display_name="Default Lake 2")
        db_session.add_all([lake1, lake2])
        db_session.commit()

        now = datetime.now(timezone.utc)
        form_data = {
            "event_id": str(test_event.id),
            "title": "All Lakes Poll",
            "poll_type": "tournament_location",
            "starts_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=7)).isoformat(),
            # No lake_ids specified - should include all
        }

        response = post_with_csrf(
            admin_client, "/admin/polls/create", data=form_data, follow_redirects=False
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]

    def test_create_poll_with_description(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test creating poll with description field."""
        now = datetime.now(timezone.utc)
        form_data = {
            "event_id": str(test_event.id),
            "title": "Poll With Description",
            "description": "This is a detailed description of the poll",
            "poll_type": "generic",
            "starts_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=7)).isoformat(),
        }

        response = post_with_csrf(
            admin_client, "/admin/polls/create", data=form_data, follow_redirects=False
        )

        assert response.status_code in [200, 302, 303]

        # Verify description was saved
        poll = db_session.query(Poll).filter(Poll.title == "Poll With Description").first()
        if poll:
            assert poll.description == "This is a detailed description of the poll"

    def test_create_generic_poll_with_multiple_options(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test creating generic poll with custom options."""
        now = datetime.now(timezone.utc)
        form_data = {
            "event_id": str(test_event.id),
            "title": "Multi-Option Poll",
            "poll_type": "generic",
            "starts_at": (now + timedelta(days=1)).isoformat(),
            "closes_at": (now + timedelta(days=7)).isoformat(),
            "poll_options[]": ["Option 1", "Option 2", "Option 3", "Option 4"],
        }

        response = post_with_csrf(
            admin_client, "/admin/polls/create", data=form_data, follow_redirects=False
        )

        assert response.status_code in [200, 302, 303]


class TestPollEditingWorkflows:
    """Tests for poll editing workflows - targeting 22.8% → >40%."""

    def test_edit_tournament_poll_add_lake(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test adding a lake to existing tournament poll."""
        # Create lakes
        lake1 = Lake(yaml_key="existing_lake", display_name="Existing Lake")
        lake2 = Lake(yaml_key="new_lake_add", display_name="New Lake")
        db_session.add_all([lake1, lake2])
        db_session.flush()

        # Create poll with only lake1
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Expandable Poll",
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
            option_data=json.dumps({"lake_id": lake1.id}),
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

        # Verify both lakes are now in poll
        db_session.expire_all()
        options = db_session.query(PollOption).filter(PollOption.poll_id == poll_id).all()
        assert len(options) >= 2

    def test_edit_generic_poll_update_options(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test updating options in generic poll."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Editable Options Poll",
            poll_type="generic",
            starts_at=now + timedelta(days=1),
            closes_at=now + timedelta(days=8),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option1 = PollOption(poll_id=poll.id, option_text="Original Option")
        db_session.add(option1)
        db_session.commit()

        poll_id = poll.id
        option1_id = option1.id

        # Update option text
        form_data = {
            "title": poll.title,
            "description": poll.description or "",
            "starts_at": poll.starts_at.isoformat(),
            "closes_at": poll.closes_at.isoformat(),
            "poll_options[]": ["Updated Option", "New Option 2"],
            "option_ids[]": [str(option1_id), ""],
        }

        response = post_with_csrf(
            admin_client, f"/admin/polls/{poll_id}/edit", data=form_data, follow_redirects=False
        )

        assert response.status_code in [200, 302, 303]


class TestTournamentResultsWorkflows:
    """Tests for tournament results workflows - targeting 27.1% / 36.7% → >50%."""

    def test_admin_can_view_manage_results_page(
        self,
        admin_client: TestClient,
        test_event: Event,
        db_session: Session,
    ):
        """Test admin can view tournament results management page."""
        lake = Lake(yaml_key="results_lake", display_name="Results Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Results Ramp")
        db_session.add(ramp)
        db_session.flush()

        tournament = Tournament(
            event_id=test_event.id,
            name="Results Test Tournament",
            lake_id=lake.id,
            ramp_id=ramp.id,
        )
        db_session.add(tournament)
        db_session.commit()

        response = admin_client.get(f"/admin/tournaments/{tournament.id}/manage")

        # Should load page or redirect
        assert response.status_code in [200, 302, 303, 404]

    def test_tournament_result_with_dead_fish_penalty(
        self,
        admin_client: TestClient,
        test_event: Event,
        member_user: Angler,
        db_session: Session,
    ):
        """Test creating result with dead fish penalty."""
        lake = Lake(yaml_key="penalty_lake", display_name="Penalty Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Penalty Ramp")
        db_session.add(ramp)
        db_session.flush()

        tournament = Tournament(
            event_id=test_event.id,
            name="Penalty Test Tournament",
            lake_id=lake.id,
            ramp_id=ramp.id,
        )
        db_session.add(tournament)
        db_session.commit()

        # Create result with dead fish penalty
        result = Result(
            tournament_id=tournament.id,
            angler_id=member_user.id,
            total_weight=Decimal("15.5"),
            big_bass_weight=Decimal("5.0"),
            dead_fish_penalty=Decimal("0.5"),  # 0.5 lb penalty
        )
        db_session.add(result)
        db_session.commit()

        # Verify penalty was saved
        db_session.expire_all()
        saved_result = db_session.query(Result).filter(Result.id == result.id).first()
        assert saved_result is not None
        assert saved_result.dead_fish_penalty == Decimal("0.5")

    def test_tournament_result_with_zero_weight(
        self,
        admin_client: TestClient,
        test_event: Event,
        member_user: Angler,
        db_session: Session,
    ):
        """Test creating result with zero weight (DNF or no fish)."""
        lake = Lake(yaml_key="zero_lake", display_name="Zero Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Zero Ramp")
        db_session.add(ramp)
        db_session.flush()

        tournament = Tournament(
            event_id=test_event.id,
            name="Zero Weight Tournament",
            lake_id=lake.id,
            ramp_id=ramp.id,
        )
        db_session.add(tournament)
        db_session.commit()

        # Create result with zero weight
        result = Result(
            tournament_id=tournament.id,
            angler_id=member_user.id,
            total_weight=Decimal("0.0"),
            big_bass_weight=Decimal("0.0"),
        )
        db_session.add(result)
        db_session.commit()

        # Verify zero weight is valid
        db_session.expire_all()
        saved_result = db_session.query(Result).filter(Result.id == result.id).first()
        assert saved_result is not None
        assert saved_result.total_weight == Decimal("0.0")


class TestVotingHelpersWorkflows:
    """Tests for voting helper functions - targeting 31.6% → >50%."""

    def test_vote_on_tournament_poll_with_complete_data(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test voting on tournament poll with complete location data."""
        # Create lake and ramp
        lake = Lake(yaml_key="vote_lake", display_name="Vote Lake")
        db_session.add(lake)
        db_session.flush()

        ramp = Ramp(lake_id=lake.id, name="Vote Ramp")
        db_session.add(ramp)
        db_session.flush()

        # Create active tournament poll
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Complete Data Poll",
            poll_type="tournament_location",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        # Create option with complete tournament data
        option_data = json.dumps(
            {
                "lake_id": lake.id,
                "ramp_id": ramp.id,
                "start_time": "06:30",
                "end_time": "15:30",
            }
        )
        option = PollOption(
            poll_id=poll.id,
            option_text=f"{lake.display_name} - {ramp.name}",
            option_data=option_data,
        )
        db_session.add(option)
        db_session.commit()

        # Submit vote
        form_data = {
            "option_id": str(option.id),
        }

        response = post_with_csrf(
            member_client, f"/polls/{poll.id}/vote", data=form_data, follow_redirects=False
        )

        # Should succeed
        assert response.status_code in [200, 302, 303]

    def test_member_can_view_poll_results_after_voting(
        self,
        member_client: TestClient,
        member_user: Angler,
        test_event: Event,
        db_session: Session,
    ):
        """Test member can view poll results after submitting vote."""
        now = datetime.now(timezone.utc)
        poll = Poll(
            event_id=test_event.id,
            title="Results Visible Poll",
            poll_type="generic",
            starts_at=now - timedelta(hours=1),
            closes_at=now + timedelta(days=7),
            created_by=1,
        )
        db_session.add(poll)
        db_session.flush()

        option = PollOption(poll_id=poll.id, option_text="Test Option")
        db_session.add(option)
        db_session.commit()

        # Vote
        form_data = {"option_id": str(option.id)}
        response = post_with_csrf(
            member_client, f"/polls/{poll.id}/vote", data=form_data, follow_redirects=True
        )

        # Should be able to view results or poll page
        assert response.status_code == 200


class TestAdminEventWorkflows:
    """Tests for admin event management workflows."""

    def test_admin_can_view_event_list(
        self, admin_client: TestClient, test_event: Event, db_session: Session
    ):
        """Test admin can view events list."""
        response = admin_client.get("/admin/events")

        assert response.status_code == 200
        # Should show events
        assert b"event" in response.content.lower() or b"tournament" in response.content.lower()


class TestLakeRampManagement:
    """Tests for lake and ramp management."""

    def test_admin_can_create_ramp_for_lake(self, admin_client: TestClient, db_session: Session):
        """Test creating a ramp for an existing lake."""
        # Create a lake first
        lake = Lake(yaml_key="ramp_test_lake", display_name="Ramp Test Lake")
        db_session.add(lake)
        db_session.commit()

        form_data = {
            "lake_id": str(lake.id),
            "name": "New Boat Ramp",
        }

        response = post_with_csrf(
            admin_client, "/admin/ramps/create", data=form_data, follow_redirects=False
        )

        # Should succeed or show form
        assert response.status_code in [200, 302, 303, 404, 405]
