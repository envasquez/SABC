from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import Base, DateTime, ForeignKey, Integer, Text, datetime, mapped_column, relationship


class Poll(Base):
    __tablename__ = "polls"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(Text, nullable=False)
    description = mapped_column(Text)
    poll_type = mapped_column(Text, nullable=False)
    event_id = mapped_column(Integer, ForeignKey("events.id"))
    created_by = mapped_column(Integer, ForeignKey("anglers.id"))
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    starts_at = mapped_column(DateTime, nullable=False)
    closes_at = mapped_column(DateTime, nullable=False)
    closed = mapped_column(Integer, default=False)
    winning_option_id = mapped_column(Integer, ForeignKey("poll_options.id"))

    event = relationship("Event", back_populates="polls")
    creator = relationship("Angler", back_populates="polls_created")
    options = relationship("PollOption", back_populates="poll", cascade="all, delete-orphan")
    votes = relationship("PollVote", back_populates="poll", cascade="all, delete-orphan")


class PollOption(Base):
    __tablename__ = "poll_options"

    id = mapped_column(Integer, primary_key=True)
    poll_id = mapped_column(Integer, ForeignKey("polls.id"), nullable=False)
    option_text = mapped_column(Text, nullable=False)
    option_data = mapped_column(Text)

    poll = relationship("Poll", back_populates="options")
    votes = relationship("PollVote", back_populates="option", cascade="all, delete-orphan")


class PollVote(Base):
    __tablename__ = "poll_votes"

    id = mapped_column(Integer, primary_key=True)
    poll_id = mapped_column(Integer, ForeignKey("polls.id"), nullable=False)
    option_id = mapped_column(Integer, ForeignKey("poll_options.id"), nullable=False)
    angler_id = mapped_column(Integer, ForeignKey("anglers.id"), nullable=False)
    voted_at = mapped_column(DateTime, default=datetime.utcnow)

    poll = relationship("Poll", back_populates="votes")
    option = relationship("PollOption", back_populates="votes")
    angler = relationship("Angler", back_populates="poll_votes")
