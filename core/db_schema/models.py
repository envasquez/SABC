"""SQLAlchemy ORM models for SABC database tables."""

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utc_now() -> datetime:
    """Return timezone-aware UTC datetime.

    Replacement for datetime.utcnow() which returns naive datetime.
    """
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


class Angler(Base):
    """Angler/User model."""

    __tablename__ = "anglers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[Optional[str]] = mapped_column(Text)
    member: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    is_admin: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    password_hash: Mapped[Optional[str]] = mapped_column(Text)
    year_joined: Mapped[Optional[int]] = mapped_column(Integer)
    phone: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)


class PasswordResetToken(Base):
    """Password reset token model."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE"), nullable=False
    )
    token: Mapped[str] = mapped_column(String, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


class Event(Base):
    """Event model."""

    __tablename__ = "events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    event_type: Mapped[Optional[str]] = mapped_column(Text, default="sabc_tournament")
    start_time: Mapped[Optional[time]] = mapped_column(Time)
    weigh_in_time: Mapped[Optional[time]] = mapped_column(Time)
    lake_name: Mapped[Optional[str]] = mapped_column(Text)
    ramp_name: Mapped[Optional[str]] = mapped_column(Text)
    entry_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=25.00)
    is_cancelled: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    holiday_name: Mapped[Optional[str]] = mapped_column(Text)


class Poll(Base):
    """Poll model."""

    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    poll_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="SET NULL")
    )
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="SET NULL")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closes_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    multiple_votes: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    winning_option_id: Mapped[Optional[int]] = mapped_column(Integer)


class PollOption(Base):
    """Poll option model."""

    __tablename__ = "poll_options"
    __table_args__ = (UniqueConstraint("poll_id", "option_text", name="uq_poll_option_text"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="CASCADE")
    )
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    option_data: Mapped[Optional[str]] = mapped_column(Text)
    display_order: Mapped[Optional[int]] = mapped_column(Integer, default=0)


class PollVote(Base):
    """Poll vote model."""

    __tablename__ = "poll_votes"
    __table_args__ = (UniqueConstraint("poll_id", "angler_id", name="uq_poll_vote_angler"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    poll_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="CASCADE")
    )
    option_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("poll_options.id", ondelete="CASCADE")
    )
    angler_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE")
    )
    voted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)
    cast_by_admin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    cast_by_admin_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="SET NULL"), nullable=True
    )


class News(Base):
    """News model."""

    __tablename__ = "news"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="SET NULL")
    )
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)
    published: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    priority: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_edited_by: Mapped[Optional[int]] = mapped_column(Integer)


class Lake(Base):
    """Lake model."""

    __tablename__ = "lakes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    yaml_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    google_maps_iframe: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)


class Ramp(Base):
    """Ramp model."""

    __tablename__ = "ramps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    lake_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lakes.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    google_maps_iframe: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=utc_now)


class Tournament(Base):
    """Tournament model."""

    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("events.id", ondelete="CASCADE")
    )
    poll_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="SET NULL")
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    lake_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("lakes.id", ondelete="SET NULL")
    )
    ramp_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("ramps.id", ondelete="SET NULL")
    )
    lake_name: Mapped[Optional[str]] = mapped_column(Text)
    ramp_name: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[Optional[time]] = mapped_column(Time)
    end_time: Mapped[Optional[time]] = mapped_column(Time)
    fish_limit: Mapped[Optional[int]] = mapped_column(Integer, default=5)
    entry_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=25.00)
    is_team: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)
    is_paper: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    big_bass_carryover: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0.0)
    complete: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="SET NULL")
    )
    limit_type: Mapped[Optional[str]] = mapped_column(Text, default="angler")
    aoy_points: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)


class Result(Base):
    """Result model."""

    __tablename__ = "results"
    __table_args__ = (
        CheckConstraint("num_fish >= 0", name="ck_result_num_fish_positive"),
        CheckConstraint("total_weight >= 0", name="ck_result_total_weight_positive"),
        CheckConstraint("big_bass_weight >= 0", name="ck_result_big_bass_weight_positive"),
        CheckConstraint("dead_fish_penalty >= 0", name="ck_result_dead_fish_penalty_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE")
    )
    angler_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE")
    )
    num_fish: Mapped[Optional[int]] = mapped_column(Integer, default=0)
    total_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0.0)
    big_bass_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0.0)
    dead_fish_penalty: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0.0)
    disqualified: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    buy_in: Mapped[Optional[bool]] = mapped_column(Boolean, default=False)
    place_finish: Mapped[Optional[int]] = mapped_column(Integer)
    was_member: Mapped[Optional[bool]] = mapped_column(Boolean, default=True)


class TeamResult(Base):
    """Team result model."""

    __tablename__ = "team_results"
    __table_args__ = (
        CheckConstraint("total_weight >= 0", name="ck_team_result_total_weight_positive"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tournament_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tournaments.id", ondelete="CASCADE")
    )
    angler1_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE")
    )
    angler2_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE")
    )
    total_weight: Mapped[Optional[Decimal]] = mapped_column(Numeric, default=0.0)
    place_finish: Mapped[Optional[int]] = mapped_column(Integer)


class OfficerPosition(Base):
    """Officer position model."""

    __tablename__ = "officer_positions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    angler_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("anglers.id", ondelete="CASCADE")
    )
    position: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    elected_date: Mapped[Optional[date]] = mapped_column(Date)
