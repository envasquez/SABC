from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import Base, Boolean, DateTime, Integer, Text, datetime, mapped_column, relationship


class Angler(Base):
    __tablename__ = "anglers"

    id = mapped_column(Integer, primary_key=True)
    name = mapped_column(Text, nullable=False)
    email = mapped_column(Text, unique=True)
    member = mapped_column(Boolean, default=True)
    is_admin = mapped_column(Boolean, default=False)
    password_hash = mapped_column(Text, name="password")
    year_joined = mapped_column(Integer)
    phone = mapped_column(Text)
    created_at = mapped_column(DateTime, default=datetime.utcnow)

    results = relationship("Result", back_populates="angler", cascade="all, delete-orphan")
    officer_positions = relationship(
        "OfficerPosition", back_populates="angler", cascade="all, delete-orphan"
    )
    polls_created = relationship("Poll", back_populates="creator")
    poll_votes = relationship("PollVote", back_populates="angler")


class OfficerPosition(Base):
    __tablename__ = "officer_positions"

    id = mapped_column(Integer, primary_key=True)
    angler_id = mapped_column(Integer, nullable=False)
    year = mapped_column(Integer, nullable=False)
    position = mapped_column(Text, nullable=False)

    angler = relationship("Angler", back_populates="officer_positions")


class News(Base):
    __tablename__ = "news"

    id = mapped_column(Integer, primary_key=True)
    title = mapped_column(Text, nullable=False)
    content = mapped_column(Text, nullable=False)
    author_id = mapped_column(Integer, nullable=False)
    created_at = mapped_column(DateTime, default=datetime.utcnow)
    updated_at = mapped_column(DateTime)
    last_edited_by = mapped_column(Integer)
    published = mapped_column(Boolean, default=False)
    priority = mapped_column(Integer, default=0)
    expires_at = mapped_column(DateTime)
