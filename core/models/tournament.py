from core.models.base import BaseModel, ConfigDict, Decimal, Optional, date, datetime, time


class TournamentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: int
    lake_name: Optional[str] = None
    ramp_name: Optional[str] = None
    entry_fee: Decimal = Decimal("25.00")
    fish_limit: int = 5
    complete: bool = False
    aoy_points: bool = False


class Tournament(TournamentBase):
    id: int
    lake_id: Optional[int] = None
    ramp_id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    limit_type: Optional[str] = None
    is_team: bool = True
    is_paper: bool = False
    poll_id: Optional[int] = None


class TournamentWithEvent(Tournament):
    event_date: date
    event_name: str
    event_description: Optional[str] = None
    event_type: str


class EventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: date
    year: int
    name: str
    description: Optional[str] = None
    event_type: str = "sabc_tournament"


class Event(EventBase):
    id: int
    start_time: Optional[time] = None
    weigh_in_time: Optional[time] = None
    lake_name: Optional[str] = None
    ramp_name: Optional[str] = None
    entry_fee: Optional[Decimal] = None
    is_cancelled: bool = False
    holiday_name: Optional[str] = None
    fish_limit: Optional[int] = None


class PollBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: Optional[str] = None
    poll_type: str
    event_id: Optional[int] = None


class Poll(PollBase):
    id: int
    created_by: Optional[int] = None
    created_at: Optional[datetime] = None
    starts_at: datetime
    closes_at: datetime
    closed: bool = False
    winning_option_id: Optional[int] = None


class LakeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    display_name: str
    yaml_key: str
    location: Optional[str] = None


class Lake(LakeBase):
    id: int
    google_maps_iframe: Optional[str] = None


class RampBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    lake_id: int
    name: str
    coordinates: Optional[str] = None


class Ramp(RampBase):
    id: int
    google_maps_iframe: Optional[str] = None
