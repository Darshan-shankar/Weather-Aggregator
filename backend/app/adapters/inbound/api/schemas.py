from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, field_serializer

from app.domain.models import WeatherReading


class FetchRequest(BaseModel):
    city: str


class ErrorResponse(BaseModel):
    detail: str


class WeatherReadingResponse(BaseModel):
    id: UUID
    city: str
    country: str
    latitude: float
    longitude: float
    timezone: str
    temperature: float
    temperature_unit: str
    wind_speed: float
    wind_speed_unit: str
    humidity: int | None
    weather_code: int
    weather_description: str
    observed_at: datetime
    fetched_at: datetime

    @field_serializer("observed_at", "fetched_at")
    def _as_utc_iso(self, value: datetime) -> str:
        return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    @classmethod
    def from_domain(cls, reading: WeatherReading) -> WeatherReadingResponse:
        loc = reading.location
        return cls(
            id=reading.id,
            city=loc.name,
            country=loc.country,
            latitude=loc.latitude,
            longitude=loc.longitude,
            timezone=loc.timezone,
            temperature=reading.temperature,
            temperature_unit=reading.temperature_unit,
            wind_speed=reading.wind_speed,
            wind_speed_unit=reading.wind_speed_unit,
            humidity=reading.humidity,
            weather_code=reading.weather_code,
            weather_description=reading.weather_description,
            observed_at=reading.observed_at,
            fetched_at=reading.fetched_at,
        )
