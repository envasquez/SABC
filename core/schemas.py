"""
Pydantic models for request/response validation.
Reduces manual form parsing and validation code.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# User/Auth models
class LoginForm(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)


class RegisterForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=6)


class ForgotPasswordForm(BaseModel):
    email: EmailStr


class ResetPasswordForm(BaseModel):
    token: str
    password: str = Field(min_length=6)


class UserUpdateForm(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    member: Optional[bool] = None
    is_admin: Optional[bool] = None
    phone: Optional[str] = None


# Tournament models
class TournamentCreateForm(BaseModel):
    event_id: int
    lake_id: int
    ramp_id: int
    entry_fee: Decimal = Field(default=Decimal("25.00"), ge=0)
    fish_limit: int = Field(default=5, ge=1, le=10)
    is_paper: bool = False


class TournamentUpdateForm(BaseModel):
    lake_name: Optional[str] = None
    ramp_name: Optional[str] = None
    entry_fee: Optional[Decimal] = Field(None, ge=0)
    fish_limit: Optional[int] = Field(None, ge=1, le=10)
    complete: Optional[bool] = None


class ResultForm(BaseModel):
    angler_id: int
    num_fish: int = Field(ge=0, le=10)
    total_weight: Decimal = Field(ge=0)
    big_bass_weight: Decimal = Field(default=Decimal("0"), ge=0)
    dead_fish_penalty: Decimal = Field(default=Decimal("0"), ge=0)
    disqualified: bool = False
    buy_in: bool = False


class TeamResultForm(BaseModel):
    angler1_id: int
    angler2_id: int
    total_weight: Decimal = Field(ge=0)

    @field_validator("angler2_id")
    def validate_different_anglers(self, v, values):
        if "angler1_id" in values and v == values["angler1_id"]:
            raise ValueError("Team members must be different")
        return v


# Poll models
class PollCreateForm(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    poll_type: str = Field(
        pattern="^(tournament_location|yes_no|multiple_choice|officer_election)$"
    )
    starts_at: datetime
    closes_at: datetime
    event_id: Optional[int] = None

    @field_validator("closes_at")
    def validate_closes_after_starts(self, v, values):
        if "starts_at" in values and v <= values["starts_at"]:
            raise ValueError("Poll must close after it starts")
        return v


class PollOptionForm(BaseModel):
    option_text: str = Field(min_length=1, max_length=200)
    option_data: dict = Field(default_factory=dict)


class TournamentLocationOptionForm(BaseModel):
    lake_id: int
    ramp_id: int
    start_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")
    end_time: str = Field(pattern="^[0-2][0-9]:[0-5][0-9]$")

    @field_validator("end_time")
    def validate_end_after_start(self, v, values):
        if "start_time" in values and v <= values["start_time"]:
            raise ValueError("End time must be after start time")
        return v


class VoteForm(BaseModel):
    option_id: int


# Event models
class EventCreateForm(BaseModel):
    date: date
    name: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    create_poll: bool = True
    year: Optional[int] = None

    @field_validator("date")
    def validate_future_date(self, v):
        if v < date.today():
            raise ValueError("Event date must be in the future")
        return v


class EventUpdateForm(BaseModel):
    date: Optional[date] = None
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None


# Lake/Ramp models
class LakeCreateForm(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    location: Optional[str] = None


class RampCreateForm(BaseModel):
    lake_id: int
    name: str = Field(min_length=1, max_length=100)
    coordinates: Optional[str] = None


# Response models
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    member: bool
    is_admin: bool
    phone: Optional[str] = None

    class Config:
        from_attributes = True


class TournamentResponse(BaseModel):
    id: int
    event_id: int
    date: date
    lake_name: str
    ramp_name: str
    entry_fee: Decimal
    complete: bool
    fish_limit: int

    class Config:
        from_attributes = True


class PollResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    poll_type: str
    starts_at: datetime
    closes_at: datetime
    winning_option_id: Optional[int]
    options: list[dict]

    class Config:
        from_attributes = True
