"""Consumer-driven contract: what *our* OpenMeteoAdapter expects from Open-Meteo.

Running this file generates pacts/weather-aggregator-open-meteo.json.
The adapter is exercised against the Pact mock service, so the expectations
below are exactly what the adapter needs - no more, no less.
"""

import pytest
from pact import EachLike, Like

from app.adapters.outbound.open_meteo.adapter import CURRENT_VARIABLES, OpenMeteoAdapter
from app.domain.exceptions import CityNotFoundError
from app.domain.models import Location
from uuid import uuid4

pytestmark = pytest.mark.contract

JSON = {"Content-Type": "application/json"}


@pytest.fixture
def adapter(pact):
    return OpenMeteoAdapter(
        geocoding_url=f"{pact.uri}/v1/search",
        forecast_url=f"{pact.uri}/v1/forecast",
    )


def test_geocoding_resolves_a_city_to_coordinates(pact, adapter):
    (
        pact.given("the city Bangalore exists")
        .upon_receiving("a geocoding request for Bangalore")
        .with_request(
            "GET",
            "/v1/search",
            query={"name": "Bangalore", "count": "1", "language": "en", "format": "json"},
        )
        .will_respond_with(
            200,
            headers=JSON,
            body={
                "results": EachLike(
                    {
                        "name": Like("Bangalore"),
                        "country": Like("India"),
                        "latitude": Like(12.97),
                        "longitude": Like(77.59),
                        "timezone": Like("Asia/Kolkata"),
                    },
                    minimum=1,
                )
            },
        )
    )

    with pact:
        geo = adapter.resolve_city("Bangalore")

    assert (geo.name, geo.country) == ("Bangalore", "India")
    assert (geo.latitude, geo.longitude) == (12.97, 77.59)


def test_geocoding_without_a_match_has_no_results_block(pact, adapter):
    (
        pact.given("no city matches Atlantis")
        .upon_receiving("a geocoding request for an unknown city")
        .with_request(
            "GET",
            "/v1/search",
            query={"name": "Atlantis", "count": "1", "language": "en", "format": "json"},
        )
        .will_respond_with(200, headers=JSON, body={"generationtime_ms": Like(0.4)})
    )

    with pact:
        with pytest.raises(CityNotFoundError):
            adapter.resolve_city("Atlantis")


def test_current_conditions_for_coordinates(pact, adapter):
    (
        pact.given("weather data exists for 12.97, 77.59")
        .upon_receiving("a current weather request")
        .with_request(
            "GET",
            "/v1/forecast",
            query={
                "latitude": "12.97",
                "longitude": "77.59",
                "current": CURRENT_VARIABLES,
                "wind_speed_unit": "kmh",
                "temperature_unit": "celsius",
                "timezone": "GMT",
            },
        )
        .will_respond_with(
            200,
            headers=JSON,
            body={
                "current": {
                    "time": Like("2026-11-04T10:00"),
                    "temperature_2m": Like(22.4),
                    "relative_humidity_2m": Like(65),
                    "wind_speed_10m": Like(14.2),
                    "weather_code": Like(3),
                }
            },
        )
    )
    location = Location(uuid4(), "Bangalore", "India", 12.97, 77.59, "Asia/Kolkata")

    with pact:
        conditions = adapter.get_current(location)

    assert conditions.weather_description == "Overcast"
    assert conditions.temperature == 22.4 and conditions.wind_speed == 14.2
    assert conditions.humidity == 65
