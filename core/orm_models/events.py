from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import (
    Base,
    CheckConstraint,
    Date,
    Decimal,
    Integer,
    Numeric,
    Text,
    Time,
    mapped_column,
    relationship,
)


class Event(Base):
    __tablename__ = "events"

    id = mapped_column(Integer, primary_key=True)
    date = mapped_column(Date, nullable=False, unique=True)
    year = mapped_column(Integer, nullable=False)
    name = mapped_column(Text, nullable=False)
    description = mapped_column(Text)
    event_type = mapped_column(
        Text,
        default="sabc_tournament",
        nullable=False,
    )
    start_time = mapped_column(Time)
    weigh_in_time = mapped_column(Time)
    lake_name = mapped_column(Text)
    ramp_name = mapped_column(Text)
    entry_fee = mapped_column(Numeric, default=Decimal("25.00"))
    is_cancelled = mapped_column(Integer, default=False)
    holiday_name = mapped_column(Text)
    fish_limit = mapped_column(Integer)

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('sabc_tournament', 'holiday', 'other_tournament', 'club_event')",
            name="check_event_type",
        ),
    )

    tournaments = relationship("Tournament", back_populates="event")
    polls = relationship("Poll", back_populates="event")
