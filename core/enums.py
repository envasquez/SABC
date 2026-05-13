from enum import Enum

# Year the club started tracking tournament data. Used by profile/roster
# aggregates (per-year breakdowns, all-time-since-start filters). Set as a
# named constant rather than hardcoding 2023 across a dozen sites so a
# future backfill of historical data only needs to be done in one place.
TOURNAMENT_DATA_START_YEAR = 2023


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
