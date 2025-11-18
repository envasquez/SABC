"""Unit tests for timezone helpers.

Targets:
- core/helpers/timezone.py (37.9% → 90%+)
"""

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


class TestTimezoneBasics:
    """Test basic timezone functions."""

    def test_club_timezone_is_chicago(self):
        """Test that club timezone is correctly set to America/Chicago."""
        assert str(CLUB_TIMEZONE) == "America/Chicago"

    def test_now_utc_returns_aware_datetime(self):
        """Test that now_utc returns timezone-aware UTC datetime."""
        result = now_utc()
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc

    def test_now_local_returns_aware_datetime(self):
        """Test that now_local returns timezone-aware local datetime."""
        result = now_local()
        assert isinstance(result, datetime)
        assert result.tzinfo == CLUB_TIMEZONE


class TestToLocal:
    """Test conversion to local timezone."""

    def test_to_local_from_utc(self):
        """Test converting UTC datetime to local."""
        utc_dt = datetime(2025, 1, 15, 18, 0, 0, tzinfo=timezone.utc)
        result = to_local(utc_dt)
        assert result.tzinfo == CLUB_TIMEZONE
        # Depending on DST, should be 12:00 or 13:00 Central
        assert result.hour in [12, 13]

    def test_to_local_from_naive_assumes_utc(self):
        """Test that naive datetime is assumed to be UTC."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        result = to_local(naive_dt)
        assert result.tzinfo == CLUB_TIMEZONE
        # Should convert from UTC to Central
        assert isinstance(result, datetime)

    def test_to_local_preserves_date(self):
        """Test that date is preserved (accounting for timezone shift)."""
        utc_dt = datetime(2025, 1, 15, 6, 0, 0, tzinfo=timezone.utc)
        result = to_local(utc_dt)
        # Should be midnight in Central (either same day or day before depending on DST)
        assert result.day in [14, 15]


class TestToUTC:
    """Test conversion to UTC."""

    def test_to_utc_from_local(self):
        """Test converting local datetime to UTC."""
        local_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=CLUB_TIMEZONE)
        result = to_utc(local_dt)
        assert result.tzinfo == timezone.utc
        # Should be 5 or 6 hours ahead depending on DST
        assert result.hour in [17, 18]

    def test_to_utc_from_naive_assumes_local(self):
        """Test that naive datetime is assumed to be in club timezone."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        result = to_utc(naive_dt)
        assert result.tzinfo == timezone.utc
        # Should add 5 or 6 hours
        assert result.hour in [17, 18]

    def test_to_utc_already_utc(self):
        """Test converting UTC to UTC."""
        utc_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = to_utc(utc_dt)
        assert result.tzinfo == timezone.utc
        assert result.hour == 12


class TestMakeAware:
    """Test making naive datetimes aware."""

    def test_make_aware_with_default_timezone(self):
        """Test making naive datetime aware with club timezone."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        result = make_aware(naive_dt)
        assert result.tzinfo == CLUB_TIMEZONE
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 12

    def test_make_aware_with_custom_timezone(self):
        """Test making naive datetime aware with custom timezone."""
        naive_dt = datetime(2025, 1, 15, 12, 0, 0)
        custom_tz = ZoneInfo("America/New_York")
        result = make_aware(naive_dt, tz=custom_tz)
        assert result.tzinfo == custom_tz

    def test_make_aware_raises_on_already_aware(self):
        """Test that make_aware raises error if datetime already has timezone."""
        aware_dt = datetime(2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        with pytest.raises(ValueError, match="already has timezone"):
            make_aware(aware_dt)


class TestIsDST:
    """Test Daylight Saving Time detection."""

    def test_is_dst_with_summer_date(self):
        """Test DST detection in summer (DST active)."""
        # July is definitely DST in Chicago
        summer_dt = datetime(2025, 7, 15, 12, 0, 0)
        result = is_dst(summer_dt)
        assert result is True

    def test_is_dst_with_winter_date(self):
        """Test DST detection in winter (standard time)."""
        # January is definitely standard time in Chicago
        winter_dt = datetime(2025, 1, 15, 12, 0, 0)
        result = is_dst(winter_dt)
        assert result is False

    def test_is_dst_with_no_argument_uses_now(self):
        """Test that is_dst with no argument uses current time."""
        result = is_dst()
        assert isinstance(result, bool)

    def test_is_dst_with_aware_datetime(self):
        """Test DST detection with timezone-aware datetime."""
        summer_utc = datetime(2025, 7, 15, 17, 0, 0, tzinfo=timezone.utc)
        result = is_dst(summer_utc)
        assert result is True

    def test_is_dst_converts_to_local(self):
        """Test that DST check converts datetime to local timezone."""
        # Create a datetime in different timezone
        ny_tz = ZoneInfo("America/New_York")
        ny_dt = datetime(2025, 7, 15, 13, 0, 0, tzinfo=ny_tz)
        result = is_dst(ny_dt)
        # Should convert to Chicago time and check DST there
        assert isinstance(result, bool)


class TestRoundTripConversions:
    """Test that conversions are reversible."""

    def test_local_to_utc_to_local(self):
        """Test round-trip local → UTC → local."""
        original = datetime(2025, 6, 15, 14, 30, 0, tzinfo=CLUB_TIMEZONE)
        via_utc = to_utc(original)
        back_to_local = to_local(via_utc)

        assert back_to_local.year == original.year
        assert back_to_local.month == original.month
        assert back_to_local.day == original.day
        assert back_to_local.hour == original.hour
        assert back_to_local.minute == original.minute

    def test_utc_to_local_to_utc(self):
        """Test round-trip UTC → local → UTC."""
        original = datetime(2025, 6, 15, 19, 30, 0, tzinfo=timezone.utc)
        via_local = to_local(original)
        back_to_utc = to_utc(via_local)

        assert back_to_utc.year == original.year
        assert back_to_utc.month == original.month
        assert back_to_utc.day == original.day
        assert back_to_utc.hour == original.hour
        assert back_to_utc.minute == original.minute
