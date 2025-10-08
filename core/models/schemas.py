"""Pydantic models for request/response validation.

These models provide type-safe data validation for API endpoints and
ensure consistency across the application.
"""

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base user model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Full name of the user")
    email: EmailStr = Field(..., description="Email address (used for login)")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    member: bool = Field(default=False, description="Whether user is a club member")
    is_admin: bool = Field(default=False, description="Whether user has admin privileges")

    model_config = ConfigDict(from_attributes=True)


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = Field(..., min_length=12, description="User password (min 12 characters)")


class UserUpdate(BaseModel):
    """Model for updating user fields (all fields optional)."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    member: Optional[bool] = None
    is_admin: Optional[bool] = None
    password: Optional[str] = Field(None, min_length=12)

    model_config = ConfigDict(from_attributes=True)


class UserResponse(UserBase):
    """Model for user responses (excludes password)."""

    id: int = Field(..., description="User ID")

    model_config = ConfigDict(from_attributes=True)


class EventBase(BaseModel):
    """Base event model with common fields."""

    name: str = Field(..., min_length=1, max_length=255, description="Event name")
    date: date = Field(..., description="Event date")
    year: int = Field(..., ge=2000, le=2100, description="Event year")
    event_type: str = Field(..., description="Type of event (tournament, meeting, etc.)")

    model_config = ConfigDict(from_attributes=True)


class EventCreate(EventBase):
    """Model for creating a new event."""

    pass


class EventResponse(EventBase):
    """Model for event responses."""

    id: int = Field(..., description="Event ID")

    model_config = ConfigDict(from_attributes=True)


class TournamentBase(BaseModel):
    """Base tournament model with common fields."""

    event_id: int = Field(..., description="Associated event ID")
    lake_id: int = Field(..., description="Lake ID")
    ramp_id: int = Field(..., description="Boat ramp ID")
    start_time: Optional[str] = Field(None, description="Tournament start time")
    end_time: Optional[str] = Field(None, description="Tournament end time")
    complete: bool = Field(default=False, description="Whether tournament is complete")

    model_config = ConfigDict(from_attributes=True)


class TournamentCreate(TournamentBase):
    """Model for creating a new tournament."""

    pass


class TournamentResponse(TournamentBase):
    """Model for tournament responses."""

    id: int = Field(..., description="Tournament ID")

    model_config = ConfigDict(from_attributes=True)


class ResultBase(BaseModel):
    """Base result model with common fields."""

    tournament_id: int = Field(..., description="Tournament ID")
    angler_id: int = Field(..., description="Angler ID")
    num_fish: int = Field(..., ge=0, le=5, description="Number of fish caught (0-5)")
    total_weight: float = Field(..., ge=0, description="Total weight in pounds")
    big_bass_weight: float = Field(default=0.0, ge=0, description="Weight of biggest bass")
    dead_fish_penalty: float = Field(default=0.0, ge=0, description="Penalty weight for dead fish")
    disqualified: bool = Field(default=False, description="Whether angler was disqualified")
    buy_in: bool = Field(default=False, description="Whether this was a buy-in entry")

    model_config = ConfigDict(from_attributes=True)


class ResultCreate(ResultBase):
    """Model for creating a new result."""

    pass


class ResultResponse(ResultBase):
    """Model for result responses."""

    id: int = Field(..., description="Result ID")
    points: Optional[float] = Field(None, description="Points earned")

    model_config = ConfigDict(from_attributes=True)


class PollBase(BaseModel):
    """Base poll model with common fields."""

    event_id: int = Field(..., description="Associated event ID")
    title: str = Field(..., min_length=1, max_length=255, description="Poll title")
    description: Optional[str] = Field(None, description="Poll description")
    poll_type: str = Field(..., description="Type of poll (location, general, etc.)")
    starts_at: datetime = Field(..., description="When poll becomes active")
    closes_at: datetime = Field(..., description="When poll closes")

    model_config = ConfigDict(from_attributes=True)


class PollCreate(PollBase):
    """Model for creating a new poll."""

    pass


class PollResponse(PollBase):
    """Model for poll responses."""

    id: int = Field(..., description="Poll ID")

    model_config = ConfigDict(from_attributes=True)


class PollOptionBase(BaseModel):
    """Base poll option model."""

    poll_id: int = Field(..., description="Poll ID")
    option_text: str = Field(..., min_length=1, max_length=500, description="Option text")
    option_data: Optional[dict] = Field(
        None, description="Structured data (lake_id, ramp_id, etc.)"
    )

    model_config = ConfigDict(from_attributes=True)


class PollOptionCreate(PollOptionBase):
    """Model for creating a new poll option."""

    pass


class PollOptionResponse(PollOptionBase):
    """Model for poll option responses."""

    id: int = Field(..., description="Option ID")
    vote_count: Optional[int] = Field(None, ge=0, description="Number of votes")

    model_config = ConfigDict(from_attributes=True)


class PollVoteCreate(BaseModel):
    """Model for casting a vote."""

    poll_id: int = Field(..., description="Poll ID")
    option_id: int = Field(..., description="Selected option ID")
    angler_id: int = Field(..., description="Voter's angler ID")

    model_config = ConfigDict(from_attributes=True)
