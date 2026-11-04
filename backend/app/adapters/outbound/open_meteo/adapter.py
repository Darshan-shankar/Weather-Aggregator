"""Outbound adapter: Open-Meteo implementation of WeatherProviderPort."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

from app.adapters.outbound.open_meteo.http_client import (
    HttpClientConfig,
    ResilientJsonClient,
)
from app.adapters.outbound.open_meteo.wmo_codes import describe_weather_code
from app.domain.exceptions import CityNotFoundError, WeatherProviderError
from app.domain.models import CurrentConditions, GeoLocation, Location
from app.ports.outbound import WeatherProviderPort

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_VARIABLES = "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code"


class OpenMeteoAdapter(WeatherProviderPort):
    def __init__(
        self,
        session: requests.Session | None = None,
        config: HttpClientConfig | None = None,
        sleep=None,
        geocoding_url: str = GEOCODING_URL,
        forecast_url: str = FORECAST_URL,
    ) -> None:
        kwargs = {"sleep": sleep} if sleep is not None else {}
        self._client = ResilientJsonClient(session or requests.Session(), config, **kwargs)
        self._geocoding_url = geocoding_url
        self._forecast_url = forecast_url

    # -- WeatherProviderPort ------------------------------------------------

    def resolve_city(self, city: str) -> GeoLocation:
        payload = self._client.get_json(
            self._geocoding_url,
            {"name": city, "count": 1, "language": "en", "format": "json"},
        )
        results = payload.get("results") if isinstance(payload, dict) else None
        if not results:
            raise CityNotFoundError(city)
        first = results[0]
        try:
            return GeoLocation(
                name=str(first["name"]),
                country=str(first.get("country", "")),
                latitude=float(first["latitude"]),
                longitude=float(first["longitude"]),
                timezone=str(first.get("timezone", "UTC")),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise self._invalid("geocoding", exc) from exc

    def get_current(self, location: Location) -> CurrentConditions:
        payload = self._client.get_json(
            self._forecast_url,
            {
                "latitude": location.latitude,
                "longitude": location.longitude,
                "current": CURRENT_VARIABLES,
                "wind_speed_unit": "kmh",
                "temperature_unit": "celsius",
                "timezone": "GMT",
            },
        )
        try:
            current: dict[str, Any] = payload["current"]
            code = int(current["weather_code"])
            humidity = current.get("relative_humidity_2m")
            return CurrentConditions(
                temperature=float(current["temperature_2m"]),
                wind_speed=float(current["wind_speed_10m"]),
                weather_code=code,
                weather_description=describe_weather_code(code),
                observed_at=self._parse_time(current["time"]),
                humidity=int(round(humidity)) if humidity is not None else None,
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise self._invalid("forecast", exc) from exc

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _parse_time(raw: str) -> datetime:
        # Open-Meteo returns "2026-11-04T10:00" in the requested timezone (GMT).
        return datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)

    @staticmethod
    def _invalid(kind: str, cause: Exception) -> WeatherProviderError:
        return WeatherProviderError(f"Weather provider returned an invalid {kind} response")
