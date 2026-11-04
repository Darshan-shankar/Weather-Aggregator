"""Outbound adapter: PostgreSQL implementation of WeatherRepositoryPort."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session, sessionmaker

from app.adapters.outbound.persistence.orm import (
    LocationAliasRow,
    LocationRow,
    WeatherReadingRow,
)
from app.domain.models import Location, WeatherReading
from app.ports.outbound import WeatherRepositoryPort

_COORD = Decimal("0.000001")


def _coord(value: float) -> Decimal:
    return Decimal(str(value)).quantize(_COORD)


def _to_location(row: LocationRow) -> Location:
    return Location(
        id=row.id,
        name=row.name,
        country=row.country,
        latitude=float(row.latitude),
        longitude=float(row.longitude),
        timezone=row.timezone,
    )


def _to_reading(row: WeatherReadingRow) -> WeatherReading:
    return WeatherReading(
        id=row.id,
        location=_to_location(row.location),
        temperature=row.temperature,
        temperature_unit=row.temperature_unit,
        wind_speed=row.wind_speed,
        wind_speed_unit=row.wind_speed_unit,
        humidity=row.humidity,
        weather_code=row.weather_code,
        weather_description=row.description,
        observed_at=row.observed_at,
        fetched_at=row.fetched_at,
    )


class PostgresWeatherRepository(WeatherRepositoryPort):
    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory

    def find_location_by_alias(self, alias: str) -> Location | None:
        with self._session_factory() as session:
            row = session.execute(
                select(LocationRow)
                .join(LocationAliasRow, LocationAliasRow.location_id == LocationRow.id)
                .where(LocationAliasRow.alias == alias)
            ).scalar_one_or_none()
            return _to_location(row) if row else None

    def save_location(self, location: Location, aliases: set[str]) -> Location:
        identity = (
            LocationRow.name == location.name,
            LocationRow.country == location.country,
            LocationRow.latitude == _coord(location.latitude),
            LocationRow.longitude == _coord(location.longitude),
        )
        with self._session_factory.begin() as session:
            # Atomic upsert: concurrent requests for a new city cannot create duplicates.
            session.execute(
                pg_insert(LocationRow)
                .values(
                    id=location.id,
                    name=location.name,
                    country=location.country,
                    latitude=_coord(location.latitude),
                    longitude=_coord(location.longitude),
                    timezone=location.timezone,
                )
                .on_conflict_do_nothing(constraint="uq_location_identity")
            )
            row = session.execute(select(LocationRow).where(*identity)).scalar_one()
            for alias in aliases:
                # An alias already owned by another location keeps its owner (first wins).
                session.execute(
                    pg_insert(LocationAliasRow)
                    .values(alias=alias, location_id=row.id)
                    .on_conflict_do_nothing(index_elements=["alias"])
                )
            return _to_location(row)

    def save_reading(self, reading: WeatherReading) -> None:
        with self._session_factory.begin() as session:
            session.add(
                WeatherReadingRow(
                    id=reading.id,
                    location_id=reading.location.id,
                    temperature=reading.temperature,
                    temperature_unit=reading.temperature_unit,
                    wind_speed=reading.wind_speed,
                    wind_speed_unit=reading.wind_speed_unit,
                    humidity=reading.humidity,
                    weather_code=reading.weather_code,
                    description=reading.weather_description,
                    observed_at=reading.observed_at,
                    fetched_at=reading.fetched_at,
                )
            )

    def find_readings(self, location_id: UUID) -> list[WeatherReading]:
        with self._session_factory() as session:
            rows = session.execute(
                select(WeatherReadingRow)
                .where(WeatherReadingRow.location_id == location_id)
                .order_by(WeatherReadingRow.fetched_at.desc())
            ).scalars()
            return [_to_reading(r) for r in rows]

    def find_latest(self, location_id: UUID) -> WeatherReading | None:
        with self._session_factory() as session:
            row = session.execute(
                select(WeatherReadingRow)
                .where(WeatherReadingRow.location_id == location_id)
                .order_by(WeatherReadingRow.fetched_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            return _to_reading(row) if row else None
