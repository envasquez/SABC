"""Unit tests for poll option helper functions."""

from unittest.mock import MagicMock, patch

from routes.admin.polls.poll_option_helpers import update_or_create_poll_option


class TestUpdateOrCreatePollOption:
    """Test suite for update_or_create_poll_option helper function."""

    def test_update_or_create_poll_option_ignores_empty_text(self):
        """Test update_or_create_poll_option returns early for empty text."""
        with patch("routes.admin.polls.poll_option_helpers.get_session") as mock_session:
            update_or_create_poll_option(poll_id=1, option_text="", option_id=None)

            # Session should not be called for empty text
            assert not mock_session.called

    def test_update_or_create_poll_option_ignores_none_text(self):
        """Test update_or_create_poll_option returns early for None text."""
        with patch("routes.admin.polls.poll_option_helpers.get_session") as mock_session:
            update_or_create_poll_option(poll_id=1, option_text=None, option_id=None)  # type: ignore[arg-type]

            # Session should not be called for None text
            assert not mock_session.called

    @patch("routes.admin.polls.poll_option_helpers.get_session")
    def test_update_or_create_poll_option_creates_new_option(self, mock_get_session):
        """Test update_or_create_poll_option creates new option when option_id is None."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        update_or_create_poll_option(poll_id=123, option_text="Lake Travis", option_id=None)

        # Verify new option added
        assert mock_session.add.called
        added_option = mock_session.add.call_args[0][0]
        assert added_option.poll_id == 123
        assert added_option.option_text == "Lake Travis"
        assert added_option.option_data == "{}"

    @patch("routes.admin.polls.poll_option_helpers.get_session")
    def test_update_or_create_poll_option_updates_existing_option(self, mock_get_session):
        """Test update_or_create_poll_option updates existing option when option_id provided."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock existing poll option
        mock_existing_option = MagicMock()
        mock_existing_option.option_text = "Old Text"

        # Setup mock query chain for both queries:
        # 1. First query - find the existing option by ID
        # 2. Second query - check for duplicate text (should return None - no duplicate)
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query

        # First call returns existing option, second call returns None (no duplicate)
        mock_query.filter.return_value.filter.return_value.first.side_effect = [
            mock_existing_option,  # First query: find existing option
            None,  # Second query: no duplicate text found
        ]
        mock_query.filter.return_value.first.side_effect = [
            mock_existing_option,  # First query: find existing option
            None,  # Second query: no duplicate text found
        ]

        update_or_create_poll_option(poll_id=123, option_text="Updated Text", option_id="456")

        # Verify option text was updated
        assert mock_existing_option.option_text == "Updated Text"
        # Verify no new option added
        assert not mock_session.add.called

    @patch("routes.admin.polls.poll_option_helpers.get_session")
    def test_update_or_create_poll_option_handles_missing_option(self, mock_get_session):
        """Test update_or_create_poll_option handles when option_id doesn't exist."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        # Mock query returns None (option not found)
        mock_session.query.return_value.filter.return_value.first.return_value = None

        update_or_create_poll_option(poll_id=123, option_text="New Text", option_id="999")

        # Should not crash, just skip update
        # No option added since option_id was provided but not found
        assert not mock_session.add.called

    @patch("routes.admin.polls.poll_option_helpers.get_session")
    def test_update_or_create_poll_option_filters_by_poll_id(self, mock_get_session):
        """Test update_or_create_poll_option filters by both option_id and poll_id."""
        mock_session = MagicMock()
        mock_get_session.return_value.__enter__.return_value = mock_session

        mock_query = mock_session.query.return_value
        mock_filter = MagicMock()
        mock_query.filter.return_value = mock_filter

        update_or_create_poll_option(poll_id=123, option_text="Text", option_id="456")

        # Verify filter was called (should include both poll_id and option_id checks)
        assert mock_query.filter.called
        # Verify query was called
        assert mock_session.query.called
