"""Open-Meteo HTTP stub built on `responses`.

Shared by the adapter, component and BDD suites so that every layer fakes
the external API in exactly the same way.
"""

from __future__ import annotations

from typing import Any

import requests
import responses
from responses import matchers

from app.adapters.outbound.open_meteo.adapter import FORECAST_URL, GEOCODING_URL


def geocoding_payload(
    name: str = "Bangalore",
    country: str = "India",
    latitude: float = 12.97,
    longitude: float = 77.59,
    timezone: str = "Asia/Kolkata",
) -> dict[str, Any]:
    return {
        "results": [
            {
                "id": 1277333,
                "name": name,
                "latitude": latitude,
                "longitude": longitude,
                "country": country,
                "timezone": timezone,
            }
        ],
        "generationtime_ms": 0.9,
    }


def forecast_payload(
    temperature: float = 22.4,
    wind_speed: float = 14.2,
    weather_code: int = 3,
    humidity: int | None = 65,
    time: str = "2026-11-04T10:00",
) -> dict[str, Any]:
    current: dict[str, Any] = {
        "time": time,
        "interval": 900,
        "temperature_2m": temperature,
        "wind_speed_10m": wind_speed,
        "weather_code": weather_code,
    }
    if humidity is not None:
        current["relative_humidity_2m"] = humidity
    return {
        "latitude": 12.97,
        "longitude": 77.59,
        "timezone": "GMT",
        "current_units": {"temperature_2m": "°C", "wind_speed_10m": "km/h"},
        "current": current,
    }


class OpenMeteoStub:
    """Registers canned Open-Meteo responses on a `responses.RequestsMock`."""

    def __init__(self, rsps: responses.RequestsMock) -> None:
        self._rsps = rsps

    def known_city(self, query: str, **geo: Any) -> None:
        geo.setdefault("name", query)
        self._rsps.add(
            responses.GET,
            GEOCODING_URL,
            json=geocoding_payload(**geo),
            match=[matchers.query_param_matcher({"name": query}, strict_match=False)],
        )

    def unknown_city(self, query: str) -> None:
        self._rsps.add(
            responses.GET,
            GEOCODING_URL,
            json={"generationtime_ms": 0.4},  # Open-Meteo omits "results" when empty
            match=[matchers.query_param_matcher({"name": query}, strict_match=False)],
        )

    def weather_at(self, latitude: float, longitude: float, **conditions: Any) -> None:
        self._rsps.add(
            responses.GET,
            FORECAST_URL,
            json=forecast_payload(**conditions),
            match=[
                matchers.query_param_matcher(
                    {"latitude": str(latitude), "longitude": str(longitude)},
                    strict_match=False,
                )
            ],
        )

    def provider_down(self) -> None:
        for url in (GEOCODING_URL, FORECAST_URL):
            self._rsps.add(responses.GET, url, status=503, json={"error": True})

    def provider_times_out(self) -> None:
        for url in (GEOCODING_URL, FORECAST_URL):
            self._rsps.add(responses.GET, url, body=requests.Timeout("simulated"))

    def calls_to(self, url: str) -> int:
        return sum(1 for call in self._rsps.calls if call.request.url.startswith(url))
