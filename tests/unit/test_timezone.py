"""Unit tests for timezone utilities."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from core.helpers.timezone import (
    CLUB_TIMEZONE,
    make_aware,
    now_local,
    now_utc,
    to_local,
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
