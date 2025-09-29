"""Tests for application enums."""

from core.enums import EventType, LimitType, PollType


class TestEventType:
    """Test EventType enum."""

    def test_event_type_values(self):
        """Test that all event type values are correct."""
        assert EventType.SABC_TOURNAMENT.value == "sabc_tournament"
        assert EventType.HOLIDAY.value == "holiday"
        assert EventType.OTHER_TOURNAMENT.value == "other_tournament"
        assert EventType.CLUB_EVENT.value == "club_event"

    def test_event_type_string_comparison(self):
        """Test that event types can be compared to strings."""
        assert EventType.SABC_TOURNAMENT == "sabc_tournament"
        assert EventType.HOLIDAY == "holiday"

    def test_event_type_in_list(self):
        """Test that event types work with 'in' operator."""
        event_types = [EventType.SABC_TOURNAMENT, EventType.HOLIDAY]
        assert EventType.SABC_TOURNAMENT in event_types
        assert EventType.CLUB_EVENT not in event_types


class TestPollType:
    """Test PollType enum."""

    def test_poll_type_values(self):
        """Test that all poll type values are correct."""
        assert PollType.TOURNAMENT_LOCATION.value == "tournament_location"
        assert PollType.GENERIC.value == "generic"

    def test_poll_type_string_comparison(self):
        """Test that poll types can be compared to strings."""
        assert PollType.TOURNAMENT_LOCATION == "tournament_location"
        assert PollType.GENERIC == "generic"


class TestLimitType:
    """Test LimitType enum."""

    def test_limit_type_values(self):
        """Test that all limit type values are correct."""
        assert LimitType.ANGLER.value == "angler"
        assert LimitType.TEAM.value == "team"

    def test_limit_type_string_comparison(self):
        """Test that limit types can be compared to strings."""
        assert LimitType.ANGLER == "angler"
        assert LimitType.TEAM == "team"
