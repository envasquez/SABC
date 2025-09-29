"""Enumerations for database and application constants."""

from enum import Enum


class EventType(str, Enum):
    """Event type enumeration matching database constraint."""

    SABC_TOURNAMENT = "sabc_tournament"
    HOLIDAY = "holiday"
    OTHER_TOURNAMENT = "other_tournament"
    CLUB_EVENT = "club_event"


class PollType(str, Enum):
    """Poll type enumeration."""

    TOURNAMENT_LOCATION = "tournament_location"
    GENERIC = "generic"


class LimitType(str, Enum):
    """Fish limit type for tournaments."""

    ANGLER = "angler"
    TEAM = "team"
