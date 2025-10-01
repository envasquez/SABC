"""Tournament-related Pydantic models."""

from core.models.base import BaseModel, ConfigDict, Optional, date, time


class TournamentBase(BaseModel):
    """Base tournament model with common fields."""

    model_config = ConfigDict(from_attributes=True)

    event_id: int
    lake_name: Optional[str] = None
    ramp_name: Optional[str] = None
    fish_limit: int = 5
    complete: bool = False
    entry_fee: Optional[int] = None


class Tournament(TournamentBase):
    """Full tournament model."""

    id: int
    lake_id: Optional[int] = None
    ramp_id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None


class TournamentWithEvent(Tournament):
    """Tournament with associated event data - used by tournament detail page."""

    event_date: date
    event_name: str
    event_description: Optional[str] = None
    event_type: str
