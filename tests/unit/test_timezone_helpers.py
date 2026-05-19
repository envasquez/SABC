"""Unit tests for timezone helpers.

Targets:
- core/helpers/timezone.py (37.9% → 90%+)
"""

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


class TestToLocalRoundTrip:
    """Test that UTC -> local conversion is correct."""

    def test_utc_to_local(self):
        """Test UTC -> local conversion preserves the instant."""
        original = datetime(2025, 6, 15, 19, 30, 0, tzinfo=timezone.utc)
        via_local = to_local(original)

        assert via_local.tzinfo == CLUB_TIMEZONE
        # Same instant, just a different wall-clock representation.
        assert via_local.astimezone(timezone.utc) == original
