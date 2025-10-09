"""Timezone utilities for consistent datetime handling across the application.

All tournament scheduling and poll timing uses Central Time (America/Chicago)
to match the South Austin Bass Club's location in Austin, Texas.
"""

from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

# Club timezone - Austin, Texas uses Central Time (UTC-6/-5)
CLUB_TIMEZONE = ZoneInfo("America/Chicago")


def now_utc() -> datetime:
    """
    Get current UTC time with timezone info.

    Returns:
        Timezone-aware datetime in UTC
    """
    return datetime.now(tz=timezone.utc)


def now_local() -> datetime:
    """
    Get current time in club's local timezone (Central Time).

    Returns:
        Timezone-aware datetime in America/Chicago timezone
    """
    return datetime.now(tz=CLUB_TIMEZONE)


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to club's local timezone.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        Timezone-aware datetime in America/Chicago timezone
    """
    if dt.tzinfo is None:
        # Assume naive datetime is UTC
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(CLUB_TIMEZONE)


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        Timezone-aware datetime in UTC
    """
    if dt.tzinfo is None:
        # Assume naive datetime is in club timezone
        dt = dt.replace(tzinfo=CLUB_TIMEZONE)
    return dt.astimezone(timezone.utc)


def make_aware(dt: datetime, tz: Optional[ZoneInfo] = None) -> datetime:
    """
    Make a naive datetime timezone-aware.

    Args:
        dt: Naive datetime to make aware
        tz: Timezone to use (defaults to CLUB_TIMEZONE)

    Returns:
        Timezone-aware datetime

    Raises:
        ValueError: If datetime already has timezone info
    """
    if dt.tzinfo is not None:
        raise ValueError(f"Datetime already has timezone info: {dt.tzinfo}")

    if tz is None:
        tz = CLUB_TIMEZONE

    return dt.replace(tzinfo=tz)


def is_dst(dt: Optional[datetime] = None) -> bool:
    """
    Check if Daylight Saving Time is in effect.

    Args:
        dt: Datetime to check (defaults to now)

    Returns:
        True if DST is in effect, False otherwise
    """
    if dt is None:
        dt = now_local()
    elif dt.tzinfo is None:
        dt = make_aware(dt)
    else:
        dt = to_local(dt)

    # DST offset is -5 hours, standard offset is -6 hours
    return dt.utcoffset().total_seconds() == -5 * 3600  # type: ignore
