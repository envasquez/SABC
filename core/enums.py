from enum import Enum


class EventType(str, Enum):
    SABC_TOURNAMENT = "sabc_tournament"
    HOLIDAY = "holiday"
    OTHER_TOURNAMENT = "other_tournament"
    CLUB_EVENT = "club_event"


class PollType(str, Enum):
    TOURNAMENT_LOCATION = "tournament_location"
    GENERIC = "generic"


class LimitType(str, Enum):
    ANGLER = "angler"
    TEAM = "team"
