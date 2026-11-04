"""SQLAlchemy table definitions. Infrastructure only: never imported by the domain."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class LocationRow(Base):
    __tablename__ = "locations"
    __table_args__ = (
        UniqueConstraint("name", "country", "latitude", "longitude", name="uq_location_identity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    country: Mapped[str] = mapped_column(String(100), default="")
    latitude: Mapped[float] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float] = mapped_column(Numeric(9, 6))
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class LocationAliasRow(Base):
    """Normalised user-typed names -> location (e.g. 'bangalore' -> Bengaluru)."""

    __tablename__ = "location_aliases"

    alias: Mapped[str] = mapped_column(String(200), primary_key=True)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE"), index=True
    )


class WeatherReadingRow(Base):
    __tablename__ = "weather_readings"
    __table_args__ = (
        Index("idx_weather_location_fetched", "location_id", "fetched_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    location_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("locations.id", ondelete="CASCADE")
    )
    temperature: Mapped[float] = mapped_column()
    temperature_unit: Mapped[str] = mapped_column(String(16))
    wind_speed: Mapped[float] = mapped_column()
    wind_speed_unit: Mapped[str] = mapped_column(String(16))
    humidity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weather_code: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(String(100))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    location: Mapped[LocationRow] = relationship(lazy="joined")
