"""In-memory fakes shared by unit tests and the component/BDD harness."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.domain.models import (
    CurrentConditions,
    GeoLocation,
    Location,
    WeatherReading,
)
from app.ports.outbound import Clock, WeatherRepositoryPort

T0 = datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)


class MutableClock(Clock):
    def __init__(self, start: datetime = T0) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, delta: timedelta) -> None:
        self._now += delta

    def set(self, value: datetime) -> None:
        self._now = value


class InMemoryWeatherRepository(WeatherRepositoryPort):
    def __init__(self) -> None:
        self.locations: dict[UUID, Location] = {}
        self.aliases: dict[str, UUID] = {}
        self.readings: list[WeatherReading] = []

    def find_location_by_alias(self, alias: str) -> Location | None:
        location_id = self.aliases.get(alias)
        return self.locations.get(location_id) if location_id else None

    def save_location(self, location: Location, aliases: set[str]) -> Location:
        existing = next(
            (
                loc
                for loc in self.locations.values()
                if (loc.name, loc.country, loc.latitude, loc.longitude)
                == (location.name, location.country, location.latitude, location.longitude)
            ),
            None,
        )
        persisted = existing or location
        self.locations[persisted.id] = persisted
        for alias in aliases:
            self.aliases.setdefault(alias, persisted.id)  # first alias owner wins
        return persisted

    def save_reading(self, reading: WeatherReading) -> None:
        self.readings.append(reading)

    def find_readings(self, location_id: UUID) -> list[WeatherReading]:
        mine = [r for r in self.readings if r.location.id == location_id]
        return sorted(mine, key=lambda r: r.fetched_at, reverse=True)

    def find_latest(self, location_id: UUID) -> WeatherReading | None:
        readings = self.find_readings(location_id)
        return readings[0] if readings else None


def make_geo(
    name: str = "Bangalore",
    country: str = "India",
    latitude: float = 12.97,
    longitude: float = 77.59,
    timezone_name: str = "Asia/Kolkata",
) -> GeoLocation:
    return GeoLocation(name, country, latitude, longitude, timezone_name)


def make_conditions(
    temperature: float = 22.4,
    wind_speed: float = 14.2,
    weather_code: int = 3,
    description: str = "Overcast",
    observed_at: datetime = T0,
    humidity: int | None = 65,
) -> CurrentConditions:
    return CurrentConditions(
        temperature=temperature,
        wind_speed=wind_speed,
        weather_code=weather_code,
        weather_description=description,
        observed_at=observed_at,
        humidity=humidity,
    )
