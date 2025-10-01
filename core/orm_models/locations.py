from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from .base import Base, ForeignKey, Integer, Text, mapped_column, relationship


class Lake(Base):
    __tablename__ = "lakes"

    id = mapped_column(Integer, primary_key=True)
    display_name = mapped_column(Text, nullable=False)
    yaml_key = mapped_column(Text, nullable=False, unique=True)
    location = mapped_column(Text)
    google_maps_iframe = mapped_column(Text)

    ramps = relationship("Ramp", back_populates="lake", cascade="all, delete-orphan")


class Ramp(Base):
    __tablename__ = "ramps"

    id = mapped_column(Integer, primary_key=True)
    lake_id = mapped_column(Integer, ForeignKey("lakes.id"), nullable=False)
    name = mapped_column(Text, nullable=False)
    coordinates = mapped_column(Text)
    google_maps_iframe = mapped_column(Text)

    lake = relationship("Lake", back_populates="ramps")
