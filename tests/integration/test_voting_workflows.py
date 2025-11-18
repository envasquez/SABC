"""Comprehensive voting workflow tests to improve coverage.

Tests voting system functionality including poll validation, tournament location votes,
and proxy voting by admins.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from core.db_schema import Angler, Event, Lake, Poll, PollOption, PollVote, Ramp
from core.helpers.timezone import now_local
from routes.voting.vote_validation import (
    get_or_create_option_id,
    validate_poll_state,
    validate_proxy_vote,
    validate_tournament_location_vote,
)


class TestPollValidation:
    """Test poll state validation."""

    def test_validate_poll_state_not_found(self, db_session: Session):
        """Test validation when poll doesn't exist."""
        error = validate_poll_state(poll_id=99999, user_id=1)
        assert error == "Poll not found"

    def test_validate_poll_state_already_voted(self, db_session: Session, member_user: Angler):
        """Test validation when user already voted."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="simple",
            starts_at=now_local() - timedelta(hours=1),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        # Create a vote
        option = PollOption(poll_id=poll.id, option_text="Option 1")
        db_session.add(option)
        db_session.commit()

        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        error = validate_poll_state(poll_id=poll.id, user_id=member_user.id)
        assert error is not None
        assert "already voted" in error.lower()

    def test_validate_poll_state_closed(self, db_session: Session, member_user: Angler):
        """Test validation when poll is closed."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Closed Poll",
            poll_type="simple",
            starts_at=now_local() - timedelta(hours=2),
            closes_at=now_local() - timedelta(hours=1),
            closed=True,
        )
        db_session.add(poll)
        db_session.commit()

        error = validate_poll_state(poll_id=poll.id, user_id=member_user.id)
        assert error is not None
        assert "closed" in error.lower()

    def test_validate_poll_state_not_started(self, db_session: Session, member_user: Angler):
        """Test validation when poll hasn't started yet."""
        event = Event(
            name="Event",
            date=datetime.now().date() + timedelta(days=7),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Future Poll",
            poll_type="simple",
            starts_at=now_local() + timedelta(hours=1),
            closes_at=now_local() + timedelta(hours=2),
        )
        db_session.add(poll)
        db_session.commit()

        error = validate_poll_state(poll_id=poll.id, user_id=member_user.id)
        assert error is not None
        assert "not accepting votes" in error.lower()


class TestTournamentLocationValidation:
    """Test tournament location vote validation."""

    def test_validate_missing_fields(self):
        """Test validation with missing required fields."""
        vote_data = {"lake_id": 1}
        option_text, error = validate_tournament_location_vote(vote_data)
        assert option_text is None
        assert error is not None
        assert "Invalid vote data" in error

    def test_validate_invalid_time_format(self, db_session: Session):
        """Test validation with invalid time format."""
        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Test Ramp")
        db_session.add(ramp)
        db_session.commit()

        vote_data = {
            "lake_id": str(lake.id),
            "ramp_id": str(ramp.id),
            "start_time": "25:00",
            "end_time": "26:00",
        }
        option_text, error = validate_tournament_location_vote(vote_data)
        assert option_text is None
        assert error is not None
        assert "Invalid time format" in error

    def test_validate_end_before_start(self, db_session: Session):
        """Test validation when end time is before start time."""
        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Test Ramp")
        db_session.add(ramp)
        db_session.commit()

        vote_data = {
            "lake_id": str(lake.id),
            "ramp_id": str(ramp.id),
            "start_time": "15:00",
            "end_time": "14:00",
        }
        option_text, error = validate_tournament_location_vote(vote_data)
        assert option_text is None
        assert error is not None
        assert "End time must be after start time" in error

    def test_validate_unreasonable_hours(self, db_session: Session):
        """Test validation with unreasonable tournament hours."""
        lake = Lake(yaml_key="test", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="Test Ramp")
        db_session.add(ramp)
        db_session.commit()

        # Start too early
        vote_data = {
            "lake_id": str(lake.id),
            "ramp_id": str(ramp.id),
            "start_time": "03:00",
            "end_time": "12:00",
        }
        option_text, error = validate_tournament_location_vote(vote_data)
        assert option_text is None
        assert error is not None
        assert "between 4:00 AM and 11:00 PM" in error

    def test_validate_valid_tournament_location(self, db_session: Session):
        """Test validation with valid tournament location data."""
        lake = Lake(yaml_key="test-lake", display_name="Test Lake")
        db_session.add(lake)
        db_session.commit()

        ramp = Ramp(lake_id=lake.id, name="test ramp")
        db_session.add(ramp)
        db_session.commit()

        vote_data = {
            "lake_id": str(lake.id),
            "ramp_id": str(ramp.id),
            "start_time": "06:00",
            "end_time": "14:00",
        }
        option_text, error = validate_tournament_location_vote(vote_data)
        assert error is None
        assert option_text is not None
        assert "Test Lake" in option_text
        assert "test ramp" in option_text.lower()


class TestGetOrCreateOptionId:
    """Test poll option creation with race condition handling."""

    def test_create_new_option(self, db_session: Session):
        """Test creating a new poll option."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="tournament_location",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        vote_data = {"lake_id": 1, "ramp_id": 1, "start_time": "06:00", "end_time": "14:00"}
        option_text = "Lake Travis - Bob Wentz (6:00 AM to 2:00 PM)"

        option_id = get_or_create_option_id(poll.id, option_text, vote_data, db_session)
        assert option_id is not None

        # Verify option was created
        option = db_session.query(PollOption).filter(PollOption.id == option_id).first()
        assert option is not None
        assert option.option_text == option_text

    def test_get_existing_option(self, db_session: Session):
        """Test getting an existing poll option (race condition)."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="tournament_location",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        # Create option first
        option_text = "Lake Travis - Bob Wentz (6:00 AM to 2:00 PM)"
        option = PollOption(poll_id=poll.id, option_text=option_text)
        db_session.add(option)
        db_session.commit()
        original_id = option.id

        # Try to create same option again
        vote_data = {"lake_id": 1, "ramp_id": 1, "start_time": "06:00", "end_time": "14:00"}
        option_id = get_or_create_option_id(poll.id, option_text, vote_data, db_session)

        # Should return the existing option ID
        assert option_id == original_id


class TestProxyVoteValidation:
    """Test admin proxy vote validation."""

    def test_proxy_vote_target_not_found(self, db_session: Session, admin_user: Angler):
        """Test proxy vote when target angler doesn't exist."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="simple",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        name, error = validate_proxy_vote(
            admin_id=admin_user.id,
            target_angler_id=99999,
            poll_id=poll.id,
            session=db_session,
        )
        assert name is None
        assert error is not None
        assert "not found" in error.lower()

    def test_proxy_vote_target_not_member(self, db_session: Session, admin_user: Angler):
        """Test proxy vote when target is not a member."""
        # Create non-member angler
        non_member = Angler(name="Non Member", email="nonmember@test.com", member=False)
        db_session.add(non_member)
        db_session.commit()

        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="simple",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        name, error = validate_proxy_vote(
            admin_id=admin_user.id,
            target_angler_id=non_member.id,
            poll_id=poll.id,
            session=db_session,
        )
        assert name is None
        assert error is not None
        assert "not a member" in error.lower()

    def test_proxy_vote_already_voted(
        self, db_session: Session, admin_user: Angler, member_user: Angler
    ):
        """Test proxy vote when target already voted."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="simple",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        option = PollOption(poll_id=poll.id, option_text="Option 1")
        db_session.add(option)
        db_session.commit()

        # Target already voted
        vote = PollVote(poll_id=poll.id, option_id=option.id, angler_id=member_user.id)
        db_session.add(vote)
        db_session.commit()

        name, error = validate_proxy_vote(
            admin_id=admin_user.id,
            target_angler_id=member_user.id,
            poll_id=poll.id,
            session=db_session,
        )
        assert name is None
        assert error is not None
        assert "already voted" in error.lower()

    def test_proxy_vote_valid(self, db_session: Session, admin_user: Angler, member_user: Angler):
        """Test valid proxy vote."""
        event = Event(
            name="Event",
            date=datetime.now().date(),
            year=datetime.now().year,
            event_type="tournament",
        )
        db_session.add(event)
        db_session.commit()

        poll = Poll(
            event_id=event.id,
            title="Test Poll",
            poll_type="simple",
            starts_at=now_local(),
            closes_at=now_local() + timedelta(hours=1),
        )
        db_session.add(poll)
        db_session.commit()

        name, error = validate_proxy_vote(
            admin_id=admin_user.id,
            target_angler_id=member_user.id,
            poll_id=poll.id,
            session=db_session,
        )
        assert error is None
        assert name == member_user.name


class TestAuthValidation:
    """Test auth validation helper."""

    def test_validate_phone_number_empty(self):
        """Test phone validation with empty input."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("")
        assert is_valid is True
        assert formatted is None
        assert error is None

    def test_validate_phone_number_valid_10_digits(self):
        """Test phone validation with 10 digits."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("5125551234")
        assert is_valid is True
        assert formatted == "(512) 555-1234"
        assert error is None

    def test_validate_phone_number_valid_11_digits(self):
        """Test phone validation with 11 digits (leading 1)."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("15125551234")
        assert is_valid is True
        assert formatted == "(512) 555-1234"
        assert error is None

    def test_validate_phone_number_with_formatting(self):
        """Test phone validation with formatting characters."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("(512) 555-1234")
        assert is_valid is True
        assert formatted == "(512) 555-1234"
        assert error is None

    def test_validate_phone_number_too_short(self):
        """Test phone validation with too few digits."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("512555")
        assert is_valid is False
        assert formatted is None
        assert "10 digits" in error

    def test_validate_phone_number_too_long(self):
        """Test phone validation with too many digits."""
        from routes.auth.validation import validate_phone_number

        is_valid, formatted, error = validate_phone_number("512555123456")
        assert is_valid is False
        assert formatted is None
        assert "too many digits" in error
