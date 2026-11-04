"""Domain entities and value objects. Pure Python: no framework imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID, uuid4

TEMPERATURE_UNIT = "celsius"
WIND_SPEED_UNIT = "kmh"


@dataclass(frozen=True)
class GeoLocation:
    """What the provider tells us about a city (no identity yet)."""

    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str


@dataclass(frozen=True)
class Location:
    """A persisted, identifiable place."""

    id: UUID
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str

    @classmethod
    def from_geo(cls, geo: GeoLocation, id: UUID | None = None) -> Location:
        return cls(
            id=id or uuid4(),
            name=geo.name,
            country=geo.country,
            latitude=geo.latitude,
            longitude=geo.longitude,
            timezone=geo.timezone,
        )


@dataclass(frozen=True)
class CurrentConditions:
    """Provider-agnostic snapshot of current weather."""

    temperature: float
    wind_speed: float
    weather_code: int
    weather_description: str
    observed_at: datetime  # when the weather was observed (UTC)
    humidity: int | None = None


@dataclass(frozen=True)
class WeatherReading:
    id: UUID
    location: Location
    temperature: float
    temperature_unit: str
    wind_speed: float
    wind_speed_unit: str
    humidity: int | None
    weather_code: int
    weather_description: str
    observed_at: datetime  # when the weather was observed
    fetched_at: datetime  # when *we* retrieved it

    @classmethod
    def create(
        cls,
        location: Location,
        conditions: CurrentConditions,
        fetched_at: datetime,
        id: UUID | None = None,
    ) -> WeatherReading:
        return cls(
            id=id or uuid4(),
            location=location,
            temperature=conditions.temperature,
            temperature_unit=TEMPERATURE_UNIT,
            wind_speed=conditions.wind_speed,
            wind_speed_unit=WIND_SPEED_UNIT,
            humidity=conditions.humidity,
            weather_code=conditions.weather_code,
            weather_description=conditions.weather_description,
            observed_at=conditions.observed_at,
            fetched_at=fetched_at,
        )


@dataclass(frozen=True)
class FetchResult:
    reading: WeatherReading
    created: bool  # False => served from the freshness window (cache hit)
