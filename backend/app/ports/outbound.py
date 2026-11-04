"""Outbound (driven) ports: what the domain needs from the outside world."""

from abc import ABC, abstractmethod
from datetime import datetime
from uuid import UUID

from app.domain.models import (
    CurrentConditions,
    GeoLocation,
    Location,
    WeatherReading,
)


class WeatherProviderPort(ABC):
    @abstractmethod
    def resolve_city(self, city: str) -> GeoLocation:
        """Resolve a city name to coordinates.

        Raises CityNotFoundError or WeatherProviderError.
        """

    @abstractmethod
    def get_current(self, location: Location) -> CurrentConditions:
        """Fetch current conditions. Raises WeatherProviderError."""


class WeatherRepositoryPort(ABC):
    @abstractmethod
    def find_location_by_alias(self, alias: str) -> Location | None: ...

    @abstractmethod
    def save_location(self, location: Location, aliases: set[str]) -> Location:
        """Upsert a location and register aliases.

        Returns the persisted location (which may be a pre-existing one).
        """

    @abstractmethod
    def save_reading(self, reading: WeatherReading) -> None: ...

    @abstractmethod
    def find_readings(self, location_id: UUID) -> list[WeatherReading]:
        """All readings for a location, most recently fetched first."""

    @abstractmethod
    def find_latest(self, location_id: UUID) -> WeatherReading | None: ...


class Clock(ABC):
    @abstractmethod
    def now(self) -> datetime:
        """Current time, timezone-aware (UTC)."""
