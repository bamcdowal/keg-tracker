import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class KegStatus(str, enum.Enum):
    empty = "empty"
    full = "full"
    on_tap = "on_tap"


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    batch_no: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String, default="")
    style: Mapped[str] = mapped_column(String, default="")
    abv: Mapped[float | None] = mapped_column(Float, nullable=True)
    brew_date: Mapped[str] = mapped_column(String, default="")
    bottling_date: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="")
    recipe_name: Mapped[str] = mapped_column(String, default="")
    batch_notes: Mapped[str] = mapped_column(String, default="")
    last_synced: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    kegs: Mapped[list["Keg"]] = relationship(back_populates="batch")


class Keg(Base):
    __tablename__ = "kegs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    label: Mapped[str] = mapped_column(String, default="")
    status: Mapped[KegStatus] = mapped_column(
        Enum(KegStatus), default=KegStatus.empty
    )
    location: Mapped[str] = mapped_column(String, default="")
    batch_id: Mapped[str | None] = mapped_column(
        ForeignKey("batches.id"), nullable=True, index=True
    )
    date_purchased: Mapped[str] = mapped_column(String, default="")
    notes: Mapped[str] = mapped_column(String, default="")

    batch: Mapped[Batch | None] = relationship(back_populates="kegs")


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, unique=True, nullable=False)


class BrewerySettings(Base):
    __tablename__ = "brewery_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, default="Blue Dog Brewing")
    has_custom_logo: Mapped[bool] = mapped_column(Boolean, default=False)


class KegEvent(Base):
    __tablename__ = "keg_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keg_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String, nullable=False)
    person: Mapped[str] = mapped_column(String, default="")
    batch_id: Mapped[str | None] = mapped_column(String, nullable=True)
    batch_name: Mapped[str] = mapped_column(String, default="")
    style: Mapped[str] = mapped_column(String, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
