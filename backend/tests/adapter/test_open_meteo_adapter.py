"""OpenMeteoAdapter against stubbed HTTP (`responses`) using realistic fixtures."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import requests
import responses

from app.adapters.outbound.open_meteo.adapter import (
    FORECAST_URL,
    GEOCODING_URL,
    OpenMeteoAdapter,
)
from app.adapters.outbound.open_meteo.http_client import HttpClientConfig
from app.domain.exceptions import CityNotFoundError, WeatherProviderError
from app.domain.models import Location
from tests.support.open_meteo_stub import (
    OpenMeteoStub,
    forecast_payload,
    geocoding_payload,
)

pytestmark = pytest.mark.adapter

LOCATION = Location(uuid4(), "Bangalore", "India", 12.97, 77.59, "Asia/Kolkata")


@pytest.fixture
def rsps():
    with responses.RequestsMock(assert_all_requests_are_fired=False) as mock:
        yield mock


@pytest.fixture
def sleeps():
    return []


@pytest.fixture
def adapter(sleeps):
    return OpenMeteoAdapter(
        config=HttpClientConfig(max_attempts=3, backoff_base=0.5),
        sleep=sleeps.append,
    )


# --- geocoding --------------------------------------------------------------


def test_resolve_city_maps_first_result(adapter, rsps):
    rsps.add(responses.GET, GEOCODING_URL, json=geocoding_payload())

    geo = adapter.resolve_city("Bangalore")

    assert (geo.name, geo.country, geo.latitude, geo.longitude, geo.timezone) == (
        "Bangalore", "India", 12.97, 77.59, "Asia/Kolkata",
    )
    query = rsps.calls[0].request.params
    assert query["name"] == "Bangalore" and query["count"] == "1"
    assert query["language"] == "en" and query["format"] == "json"


def test_resolve_city_without_results_means_city_not_found(adapter, rsps):
    OpenMeteoStub(rsps).unknown_city("Atlantis")

    with pytest.raises(CityNotFoundError):
        adapter.resolve_city("Atlantis")


def test_resolve_city_with_malformed_result_is_a_provider_error(adapter, rsps):
    rsps.add(responses.GET, GEOCODING_URL, json={"results": [{"name": "X"}]})

    with pytest.raises(WeatherProviderError, match="invalid geocoding"):
        adapter.resolve_city("X")


# --- current weather --------------------------------------------------------


def test_get_current_maps_payload_to_domain_conditions(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, json=forecast_payload(weather_code=61, humidity=80))

    conditions = adapter.get_current(LOCATION)

    assert conditions.temperature == 22.4
    assert conditions.wind_speed == 14.2
    assert conditions.weather_code == 61
    assert conditions.weather_description == "Rain: slight"
    assert conditions.humidity == 80
    assert conditions.observed_at == datetime(2026, 11, 4, 10, 0, tzinfo=timezone.utc)
    query = rsps.calls[0].request.params
    assert query["latitude"] == "12.97" and query["longitude"] == "77.59"
    assert query["wind_speed_unit"] == "kmh"
    assert "temperature_2m" in query["current"]


def test_get_current_tolerates_missing_humidity(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, json=forecast_payload(humidity=None))

    assert adapter.get_current(LOCATION).humidity is None


def test_unknown_weather_code_gets_a_fallback_description(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, json=forecast_payload(weather_code=42))

    assert adapter.get_current(LOCATION).weather_description == "Unknown weather code (42)"


def test_missing_current_block_is_a_provider_error(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, json={"latitude": 1})

    with pytest.raises(WeatherProviderError, match="invalid forecast"):
        adapter.get_current(LOCATION)


# --- failure handling, timeouts and retries -----------------------------------


def test_requests_are_sent_with_connect_and_read_timeouts(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, json=forecast_payload())

    adapter.get_current(LOCATION)

    assert rsps.calls[0].request.req_kwargs["timeout"] == (3.0, 10.0)


def test_timeout_is_retried_with_exponential_backoff_then_translated(adapter, rsps, sleeps):
    rsps.add(responses.GET, FORECAST_URL, body=requests.Timeout("slow"))

    with pytest.raises(WeatherProviderError, match="timed out") as info:
        adapter.get_current(LOCATION)

    assert len(rsps.calls) == 3
    assert sleeps == [0.5, 1.0]
    assert isinstance(info.value.__cause__, requests.Timeout)  # cause preserved


def test_connection_error_is_translated(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, body=requests.ConnectionError("refused"))

    with pytest.raises(WeatherProviderError, match="unavailable"):
        adapter.get_current(LOCATION)


def test_rate_limit_then_success_honours_retry_after(adapter, rsps, sleeps):
    rsps.add(responses.GET, FORECAST_URL, status=429, headers={"Retry-After": "2"})
    rsps.add(responses.GET, FORECAST_URL, json=forecast_payload())

    conditions = adapter.get_current(LOCATION)

    assert conditions.temperature == 22.4
    assert len(rsps.calls) == 2
    assert sleeps == [2.0]


def test_server_errors_exhaust_the_retry_budget(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, status=500)

    with pytest.raises(WeatherProviderError, match="HTTP 500"):
        adapter.get_current(LOCATION)

    assert len(rsps.calls) == 3


def test_client_errors_are_not_retried(adapter, rsps, sleeps):
    rsps.add(responses.GET, FORECAST_URL, status=400, json={"reason": "bad"})

    with pytest.raises(WeatherProviderError, match="HTTP 400"):
        adapter.get_current(LOCATION)

    assert len(rsps.calls) == 1 and sleeps == []


def test_invalid_json_is_translated_without_retry(adapter, rsps):
    rsps.add(responses.GET, FORECAST_URL, body="<html>oops</html>")

    with pytest.raises(WeatherProviderError, match="invalid JSON"):
        adapter.get_current(LOCATION)

    assert len(rsps.calls) == 1
