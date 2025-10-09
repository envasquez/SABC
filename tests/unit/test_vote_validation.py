"""Unit tests for voting validation functions."""

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

from routes.voting.vote_validation import (
    get_or_create_option_id,
    validate_poll_state,
    validate_tournament_location_vote,
)


class TestValidatePollState:
    """Tests for validate_poll_state function."""

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_error_for_nonexistent_poll(self, mock_get_session: Mock):
        """Test returns error message when poll doesn't exist."""
        mock_session = MagicMock()
        mock_session.query().filter().first.return_value = None
        mock_session.query().scalar.return_value = False
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(999, 1)

        assert result == "Poll not found"

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_error_when_already_voted(self, mock_get_session: Mock):
        """Test returns error when user has already voted."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = True  # Already voted
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(1, 1)

        assert result == "Poll not found, already voted, or closed"

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_error_when_poll_closed(self, mock_get_session: Mock):
        """Test returns error when poll is closed."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = False  # Not voted

        # Mock poll with closed=True
        mock_poll = MagicMock()
        mock_poll.closed = True
        mock_session.query().filter().first.return_value = mock_poll
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(1, 1)

        assert result == "Poll not found, already voted, or closed"

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_error_when_poll_not_started(self, mock_get_session: Mock):
        """Test returns error when poll hasn't started yet."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = False

        # Mock poll that starts in the future
        mock_poll = MagicMock()
        mock_poll.closed = False
        future_time = datetime.now(timezone.utc) + timedelta(days=1)
        mock_poll.starts_at = future_time
        mock_poll.closes_at = future_time + timedelta(days=7)
        mock_session.query().filter().first.return_value = mock_poll
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(1, 1)

        assert result == "Poll not accepting votes"

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_error_when_poll_ended(self, mock_get_session: Mock):
        """Test returns error when poll has ended."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = False

        # Mock poll that ended in the past
        mock_poll = MagicMock()
        mock_poll.closed = False
        past_time = datetime.now(timezone.utc) - timedelta(days=7)
        mock_poll.starts_at = past_time - timedelta(days=1)
        mock_poll.closes_at = past_time
        mock_session.query().filter().first.return_value = mock_poll
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(1, 1)

        assert result == "Poll not accepting votes"

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_none_for_valid_poll(self, mock_get_session: Mock):
        """Test returns None when poll state is valid."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = False  # Not voted

        # Mock active poll
        mock_poll = MagicMock()
        mock_poll.closed = False
        now = datetime.now(timezone.utc)
        mock_poll.starts_at = now - timedelta(days=1)
        mock_poll.closes_at = now + timedelta(days=6)
        mock_session.query().filter().first.return_value = mock_poll
        mock_get_session.return_value.__enter__.return_value = mock_session

        result = validate_poll_state(1, 1)

        assert result is None

    @patch("routes.voting.vote_validation.get_session")
    def test_handles_naive_datetime_objects(self, mock_get_session: Mock):
        """Test handles poll times without timezone info."""
        mock_session = MagicMock()
        mock_session.query().scalar.return_value = False

        # Mock poll with naive datetimes
        mock_poll = MagicMock()
        mock_poll.closed = False
        now = datetime.now()  # Naive datetime
        mock_poll.starts_at = now - timedelta(days=1)
        mock_poll.closes_at = now + timedelta(days=6)
        mock_session.query().filter().first.return_value = mock_poll
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Should not raise exception
        result = validate_poll_state(1, 1)

        # Should return None (valid) since dates are close enough
        assert result is None


class TestValidateTournamentLocationVote:
    """Tests for validate_tournament_location_vote function."""

    @patch("routes.voting.vote_validation.time_format_filter")
    @patch("routes.voting.vote_validation.find_ramp_name_by_id")
    @patch("routes.voting.vote_validation.find_lake_by_id")
    @patch("routes.voting.vote_validation.validate_lake_ramp_combo")
    def test_validates_complete_vote_data(
        self,
        mock_validate_combo: Mock,
        mock_find_lake: Mock,
        mock_find_ramp: Mock,
        mock_time_format: Mock,
    ):
        """Test validates vote data with all required fields."""
        vote_data = {
            "lake_id": "1",
            "ramp_id": "2",
            "start_time": "06:00",
            "end_time": "15:00",
        }
        mock_validate_combo.return_value = True
        mock_find_lake.return_value = "Lake Travis"
        mock_find_ramp.return_value = "Mansfield Dam"
        mock_time_format.side_effect = lambda x: f"{x} AM"

        option_text, error = validate_tournament_location_vote(vote_data)

        assert error is None
        assert "Lake Travis" in option_text
        assert "Mansfield Dam" in option_text
        assert "06:00 AM" in option_text
        assert "15:00 AM" in option_text

    def test_returns_error_for_missing_lake_id(self):
        """Test returns error when lake_id is missing."""
        vote_data = {"ramp_id": "2", "start_time": "06:00", "end_time": "15:00"}

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Invalid vote data"

    def test_returns_error_for_missing_ramp_id(self):
        """Test returns error when ramp_id is missing."""
        vote_data = {"lake_id": "1", "start_time": "06:00", "end_time": "15:00"}

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Invalid vote data"

    def test_returns_error_for_missing_start_time(self):
        """Test returns error when start_time is missing."""
        vote_data = {"lake_id": "1", "ramp_id": "2", "end_time": "15:00"}

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Invalid vote data"

    def test_returns_error_for_missing_end_time(self):
        """Test returns error when end_time is missing."""
        vote_data = {"lake_id": "1", "ramp_id": "2", "start_time": "06:00"}

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Invalid vote data"

    @patch("routes.voting.vote_validation.validate_lake_ramp_combo")
    def test_returns_error_for_invalid_lake_ramp_combo(self, mock_validate_combo: Mock):
        """Test returns error when lake/ramp combo is invalid."""
        vote_data = {
            "lake_id": "1",
            "ramp_id": "99",  # Invalid ramp for this lake
            "start_time": "06:00",
            "end_time": "15:00",
        }
        mock_validate_combo.return_value = False

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Invalid vote data"

    @patch("routes.voting.vote_validation.find_ramp_name_by_id")
    @patch("routes.voting.vote_validation.find_lake_by_id")
    @patch("routes.voting.vote_validation.validate_lake_ramp_combo")
    def test_returns_error_when_lake_not_found(
        self, mock_validate_combo: Mock, mock_find_lake: Mock, mock_find_ramp: Mock
    ):
        """Test returns error when lake doesn't exist."""
        vote_data = {
            "lake_id": "999",
            "ramp_id": "2",
            "start_time": "06:00",
            "end_time": "15:00",
        }
        mock_validate_combo.return_value = True
        mock_find_lake.return_value = None  # Lake not found
        mock_find_ramp.return_value = "Some Ramp"

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Lake or ramp not found"

    @patch("routes.voting.vote_validation.find_ramp_name_by_id")
    @patch("routes.voting.vote_validation.find_lake_by_id")
    @patch("routes.voting.vote_validation.validate_lake_ramp_combo")
    def test_returns_error_when_ramp_not_found(
        self, mock_validate_combo: Mock, mock_find_lake: Mock, mock_find_ramp: Mock
    ):
        """Test returns error when ramp doesn't exist."""
        vote_data = {
            "lake_id": "1",
            "ramp_id": "999",
            "start_time": "06:00",
            "end_time": "15:00",
        }
        mock_validate_combo.return_value = True
        mock_find_lake.return_value = "Lake Travis"
        mock_find_ramp.return_value = None  # Ramp not found

        option_text, error = validate_tournament_location_vote(vote_data)

        assert option_text is None
        assert error == "Lake or ramp not found"


class TestGetOrCreateOptionId:
    """Tests for get_or_create_option_id function."""

    @patch("routes.voting.vote_validation.get_session")
    def test_returns_existing_option_id(self, mock_get_session: Mock):
        """Test returns ID of existing option."""
        mock_session = MagicMock()
        mock_option = MagicMock()
        mock_option.id = 42
        mock_session.query().filter().filter().first.return_value = mock_option
        mock_get_session.return_value.__enter__.return_value = mock_session

        vote_data = {"lake_id": "1", "ramp_id": "2"}
        result = get_or_create_option_id(1, "Test Option", vote_data)

        assert result == 42
        # Should not have called add() since option exists
        mock_session.add.assert_not_called()

    @patch("routes.voting.vote_validation.get_session")
    def test_creates_new_option_when_not_exists(self, mock_get_session: Mock):
        """Test creates new option when it doesn't exist."""
        mock_session = MagicMock()
        mock_session.query().filter().filter().first.return_value = None  # No existing

        # Mock the new option's ID after flush
        def side_effect_flush():
            # Simulate the option getting an ID after flush
            pass

        mock_session.flush.side_effect = side_effect_flush
        mock_get_session.return_value.__enter__.return_value = mock_session

        vote_data = {"lake_id": "1", "ramp_id": "2"}
        get_or_create_option_id(1, "New Option", vote_data)

        # Should have called add() and flush()
        mock_session.add.assert_called_once()
        mock_session.flush.assert_called_once()

    @patch("routes.voting.vote_validation.get_session")
    def test_converts_lake_id_to_int(self, mock_get_session: Mock):
        """Test converts lake_id string to int before storing."""
        mock_session = MagicMock()
        mock_session.query().filter().filter().first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        vote_data = {"lake_id": "123", "ramp_id": "2"}  # String lake_id
        get_or_create_option_id(1, "Option", vote_data)

        # Verify PollOption was created with converted lake_id
        add_call = mock_session.add.call_args[0][0]
        stored_data = json.loads(add_call.option_data)
        assert stored_data["lake_id"] == 123  # Should be int
        assert isinstance(stored_data["lake_id"], int)

    @patch("routes.voting.vote_validation.get_session")
    def test_stores_vote_data_as_json(self, mock_get_session: Mock):
        """Test stores vote data as JSON string."""
        mock_session = MagicMock()
        mock_session.query().filter().filter().first.return_value = None
        mock_get_session.return_value.__enter__.return_value = mock_session

        vote_data = {
            "lake_id": "1",
            "ramp_id": "2",
            "start_time": "06:00",
            "end_time": "15:00",
        }
        get_or_create_option_id(1, "Option", vote_data)

        add_call = mock_session.add.call_args[0][0]
        # Should be able to parse the stored JSON
        parsed_data = json.loads(add_call.option_data)
        assert parsed_data["ramp_id"] == "2"
        assert parsed_data["start_time"] == "06:00"
