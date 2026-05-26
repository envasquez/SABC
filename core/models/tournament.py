"""Tournament-related Pydantic models."""

from datetime import date, time
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


class TournamentBase(BaseModel):
    """Base tournament model with common fields.

    Kept as the inheritance root for TournamentWithEvent. Not exported
    on its own — there are no callers outside this module.
    """

    model_config = ConfigDict(from_attributes=True)

    event_id: int
    lake_name: Optional[str] = None
    ramp_name: Optional[str] = None
    fish_limit: int = 5
    complete: bool = False
    entry_fee: Optional[int] = None


class TournamentWithEvent(TournamentBase):
    """Tournament + associated event data — used by the tournament detail page."""

    # Fields previously on an intermediate `Tournament` class (now removed —
    # nothing outside core.models imported it).
    id: int
    lake_id: Optional[int] = None
    ramp_id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None

    event_date: date
    event_name: str
    event_description: Optional[str] = None
    event_type: str
    big_bass_carryover: Decimal = Decimal("0.00")
    aoy_points: bool = True
