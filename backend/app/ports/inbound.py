"""Inbound (driving) port: the use cases the application offers."""

from abc import ABC, abstractmethod

from app.domain.models import FetchResult, WeatherReading


class WeatherUseCase(ABC):
    @abstractmethod
    def fetch_and_store(self, city: str, force_refresh: bool = False) -> FetchResult: ...

    @abstractmethod
    def get_readings(self, city: str) -> list[WeatherReading]: ...

    @abstractmethod
    def get_latest(self, city: str) -> WeatherReading: ...
