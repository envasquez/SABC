from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import (
    Base,
    Boolean,
    Decimal,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    Time,
    mapped_column,
    relationship,
)


class Tournament(Base):
    __tablename__ = "tournaments"

    id = mapped_column(Integer, primary_key=True)
    event_id = mapped_column(Integer, ForeignKey("events.id"), nullable=False)
    lake_id = mapped_column(Integer, ForeignKey("lakes.id"))
    ramp_id = mapped_column(Integer, ForeignKey("ramps.id"))
    lake_name = mapped_column(Text)
    ramp_name = mapped_column(Text)
    entry_fee = mapped_column(Numeric, default=Decimal("25.00"))
    fish_limit = mapped_column(Integer, default=5)
    start_time = mapped_column(Time)
    end_time = mapped_column(Time)
    complete = mapped_column(Boolean, default=False)
    is_team = mapped_column(Boolean, default=True)
    is_paper = mapped_column(Boolean, default=False)
    aoy_points = mapped_column(Boolean, default=True)
    limit_type = mapped_column(Text)
    poll_id = mapped_column(Integer, ForeignKey("polls.id"))

    event = relationship("Event", back_populates="tournaments")
    lake = relationship("Lake")
    ramp = relationship("Ramp")
    poll = relationship("Poll")
    results = relationship("Result", back_populates="tournament", cascade="all, delete-orphan")
    team_results = relationship(
        "TeamResult", back_populates="tournament", cascade="all, delete-orphan"
    )


class Result(Base):
    __tablename__ = "results"

    id = mapped_column(Integer, primary_key=True)
    tournament_id = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    angler_id = mapped_column(Integer, ForeignKey("anglers.id"), nullable=False)
    num_fish = mapped_column(Integer, default=0)
    total_weight = mapped_column(Numeric, default=Decimal("0"))
    big_bass_weight = mapped_column(Numeric, default=Decimal("0"))
    dead_fish_penalty = mapped_column(Numeric, default=Decimal("0"))
    buy_in = mapped_column(Boolean, default=False)
    disqualified = mapped_column(Boolean, default=False)

    tournament = relationship("Tournament", back_populates="results")
    angler = relationship("Angler", back_populates="results")


class TeamResult(Base):
    __tablename__ = "team_results"

    id = mapped_column(Integer, primary_key=True)
    tournament_id = mapped_column(Integer, ForeignKey("tournaments.id"), nullable=False)
    angler1_id = mapped_column(Integer, ForeignKey("anglers.id"), nullable=False)
    angler2_id = mapped_column(Integer, ForeignKey("anglers.id"))
    total_weight = mapped_column(Numeric, default=Decimal("0"))
    place_finish = mapped_column(Integer, default=0)

    tournament = relationship("Tournament", back_populates="team_results")
    angler1 = relationship("Angler", foreign_keys=[angler1_id])
    angler2 = relationship("Angler", foreign_keys=[angler2_id])
