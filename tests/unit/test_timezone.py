"""Unit tests for timezone utilities."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from core.helpers.timezone import (
    CLUB_TIMEZONE,
    is_dst,
    make_aware,
    now_local,
    now_utc,
    to_local,
    to_utc,
)


class TestTimezoneUtilities:
    """Tests for timezone utility functions."""

    def test_club_timezone_is_chicago(self):
        """Test that CLUB_TIMEZONE is America/Chicago."""
        assert CLUB_TIMEZONE == ZoneInfo("America/Chicago")

    def test_now_utc_returns_aware_datetime(self):
        """Test that now_utc() returns timezone-aware datetime in UTC."""
        result = now_utc()
        assert result.tzinfo == timezone.utc
        assert result.tzinfo is not None

    def test_now_local_returns_aware_datetime(self):
        """Test that now_local() returns timezone-aware datetime in Central Time."""
        result = now_local()
        assert result.tzinfo == CLUB_TIMEZONE
        assert result.tzinfo is not None

    def test_to_local_converts_utc_to_central(self):
        """Test converting UTC datetime to Central Time."""
        utc_time = datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc)
        local_time = to_local(utc_time)

        assert local_time.tzinfo == CLUB_TIMEZONE
        # July is CDT (UTC-5)
        assert local_time.hour == 7  # 12:00 UTC = 07:00 CDT

    def test_to_local_handles_naive_datetime(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_time = datetime(2024, 7, 1, 12, 0, 0)
        local_time = to_local(naive_time)

        assert local_time.tzinfo == CLUB_TIMEZONE
        assert local_time.hour == 7  # Assumed UTC, converted to CDT

    def test_to_utc_converts_central_to_utc(self):
        """Test converting Central Time to UTC."""
        local_time = datetime(2024, 7, 1, 12, 0, 0, tzinfo=CLUB_TIMEZONE)
        utc_time = to_utc(local_time)

        assert utc_time.tzinfo == timezone.utc
        # July is CDT (UTC-5), so 12:00 CDT = 17:00 UTC
        assert utc_time.hour == 17

    def test_to_utc_handles_naive_datetime(self):
        """Test that naive datetime is assumed to be in club timezone."""
        naive_time = datetime(2024, 7, 1, 12, 0, 0)
        utc_time = to_utc(naive_time)

        assert utc_time.tzinfo == timezone.utc
        # Assumed CDT, so 12:00 = 17:00 UTC
        assert utc_time.hour == 17

    def test_make_aware_adds_timezone(self):
        """Test that make_aware() adds timezone to naive datetime."""
        naive_time = datetime(2024, 7, 1, 12, 0, 0)
        aware_time = make_aware(naive_time)

        assert aware_time.tzinfo == CLUB_TIMEZONE
        assert aware_time.year == 2024
        assert aware_time.month == 7
        assert aware_time.day == 1
        assert aware_time.hour == 12

    def test_make_aware_raises_on_already_aware(self):
        """Test that make_aware() raises error for already-aware datetime."""
        aware_time = datetime(2024, 7, 1, 12, 0, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="already has timezone"):
            make_aware(aware_time)

    def test_make_aware_with_custom_timezone(self):
        """Test that make_aware() accepts custom timezone."""
        naive_time = datetime(2024, 7, 1, 12, 0, 0)
        eastern = ZoneInfo("America/New_York")
        aware_time = make_aware(naive_time, tz=eastern)

        assert aware_time.tzinfo == eastern

    def test_is_dst_summer(self):
        """Test DST detection for summer month (July)."""
        summer_time = datetime(2024, 7, 1, 12, 0, 0, tzinfo=CLUB_TIMEZONE)
        assert is_dst(summer_time) is True

    def test_is_dst_winter(self):
        """Test DST detection for winter month (January)."""
        winter_time = datetime(2024, 1, 1, 12, 0, 0, tzinfo=CLUB_TIMEZONE)
        assert is_dst(winter_time) is False

    def test_is_dst_handles_naive_datetime(self):
        """Test that is_dst() handles naive datetime."""
        naive_time = datetime(2024, 7, 1, 12, 0, 0)
        # Should make it aware and check DST
        result = is_dst(naive_time)
        assert result is True  # July is DST

    def test_is_dst_defaults_to_current_time(self):
        """Test that is_dst() works without parameter."""
        result = is_dst()
        assert isinstance(result, bool)

    def test_dst_transition_spring_forward(self):
        """Test DST transition in March (spring forward)."""
        # March 10, 2024 - DST starts
        before_dst = datetime(2024, 3, 10, 1, 0, 0, tzinfo=CLUB_TIMEZONE)
        after_dst = datetime(2024, 3, 10, 3, 0, 0, tzinfo=CLUB_TIMEZONE)

        assert is_dst(before_dst) is False  # CST
        assert is_dst(after_dst) is True  # CDT

    def test_dst_transition_fall_back(self):
        """Test DST transition in November (fall back)."""
        # November 3, 2024 - DST ends
        during_dst = datetime(2024, 11, 3, 0, 0, 0, tzinfo=CLUB_TIMEZONE)
        after_dst = datetime(2024, 11, 3, 2, 0, 0, tzinfo=CLUB_TIMEZONE)

        assert is_dst(during_dst) is True  # CDT
        assert is_dst(after_dst) is False  # CST
