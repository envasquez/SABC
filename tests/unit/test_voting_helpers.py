"""Unit tests for voting helper functions."""

from unittest.mock import MagicMock, patch

from routes.voting.helpers import get_poll_options, process_closed_polls


class TestGetPollOptions:
    """Test suite for get_poll_options helper function."""

    @patch("routes.voting.helpers.engine")
    def test_get_poll_options_calls_query_service(self, mock_engine):
        """Test get_poll_options delegates to QueryService."""
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        mock_qs = MagicMock()
        mock_qs.get_poll_options_with_votes.return_value = [
            {"id": 1, "option_text": "Lake Travis", "vote_count": 5},
            {"id": 2, "option_text": "Lake Austin", "vote_count": 3},
        ]

        with patch("routes.voting.helpers.QueryService", return_value=mock_qs):
            result = get_poll_options(poll_id=123, is_admin=False)

        assert len(result) == 2
        assert result[0]["option_text"] == "Lake Travis"
        mock_qs.get_poll_options_with_votes.assert_called_once_with(123, include_details=False)

    @patch("routes.voting.helpers.engine")
    def test_get_poll_options_admin_mode(self, mock_engine):
        """Test get_poll_options passes admin flag correctly."""
        mock_conn = MagicMock()
        mock_engine.connect.return_value.__enter__.return_value = mock_conn

        mock_qs = MagicMock()
        mock_qs.get_poll_options_with_votes.return_value = []

        with patch("routes.voting.helpers.QueryService", return_value=mock_qs):
            get_poll_options(poll_id=456, is_admin=True)

        mock_qs.get_poll_options_with_votes.assert_called_once_with(456, include_details=True)


class TestProcessClosedPolls:
    """Test suite for process_closed_polls helper function."""

    def test_process_closed_polls_no_polls(self, db_session):
        """Test process_closed_polls returns 0 when no polls to process."""
        result = process_closed_polls()

        assert result == 0

    def test_process_closed_polls_handles_exceptions(self, db_session):
        """Test process_closed_polls returns 0 on database errors."""
        with patch("routes.voting.helpers.get_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database error")

            result = process_closed_polls()

            assert result == 0

    # NOTE: More complex database integration tests for process_closed_polls
    # would provide better value than mocking the entire SQLAlchemy query chain.
    # The function involves complex database queries that are difficult to mock accurately.
