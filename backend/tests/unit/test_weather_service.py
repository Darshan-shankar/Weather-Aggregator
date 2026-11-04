"""Unit tests for WeatherService: both ports are stubbed, no I/O of any kind."""

from datetime import timedelta
from unittest.mock import create_autospec

import pytest

from app.domain.exceptions import (
    CityNotFoundError,
    NoReadingsFoundError,
    WeatherProviderError,
)
from app.domain.freshness import FreshnessPolicy
from app.ports.outbound import WeatherProviderPort
from app.services.weather_service import WeatherService
from tests.support.fakes import (
    InMemoryWeatherRepository,
    MutableClock,
    make_conditions,
    make_geo,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def provider():
    stub = create_autospec(WeatherProviderPort, instance=True)
    stub.resolve_city.return_value = make_geo()
    stub.get_current.return_value = make_conditions()
    return stub


@pytest.fixture
def repository():
    return InMemoryWeatherRepository()


@pytest.fixture
def clock():
    return MutableClock()


@pytest.fixture
def service(provider, repository, clock):
    return WeatherService(
        provider, repository, clock, FreshnessPolicy(max_age=timedelta(minutes=5))
    )


# --- fetch_and_store: the three mandatory cases ----------------------------


def test_successful_fetch_stores_and_returns_reading(service, provider, repository, clock):
    result = service.fetch_and_store("Bangalore")

    assert result.created is True
    reading = result.reading
    assert reading.location.name == "Bangalore"
    assert reading.temperature == 22.4
    assert reading.temperature_unit == "celsius"
    assert reading.wind_speed == 14.2
    assert reading.wind_speed_unit == "kmh"
    assert reading.weather_description == "Overcast"
    assert reading.fetched_at == clock.now()
    assert reading.observed_at == make_conditions().observed_at
    assert repository.readings == [reading]
    provider.resolve_city.assert_called_once_with("Bangalore")
    provider.get_current.assert_called_once()


def test_external_api_failure_propagates_and_stores_nothing(service, provider, repository):
    provider.get_current.side_effect = WeatherProviderError("Weather provider unavailable")

    with pytest.raises(WeatherProviderError):
        service.fetch_and_store("Bangalore")

    assert repository.readings == []


def test_geocoding_failure_propagates_and_stores_nothing(service, provider, repository):
    provider.resolve_city.side_effect = WeatherProviderError("timed out")

    with pytest.raises(WeatherProviderError):
        service.fetch_and_store("Bangalore")

    assert repository.readings == []
    provider.get_current.assert_not_called()


def test_city_not_found_raises_and_never_asks_for_weather(service, provider, repository):
    provider.resolve_city.side_effect = CityNotFoundError("Atlantis")

    with pytest.raises(CityNotFoundError):
        service.fetch_and_store("Atlantis")

    provider.get_current.assert_not_called()
    assert repository.readings == []
    assert repository.locations == {}


# --- caching (freshness window) -------------------------------------------


def test_second_fetch_within_window_is_served_from_cache(service, provider, repository, clock):
    first = service.fetch_and_store("Bangalore")
    clock.advance(timedelta(minutes=4, seconds=59))

    second = service.fetch_and_store("Bangalore")

    assert second.created is False
    assert second.reading == first.reading
    assert provider.get_current.call_count == 1
    assert provider.resolve_city.call_count == 1
    assert len(repository.readings) == 1


def test_fetch_after_window_expires_calls_provider_again(service, provider, repository, clock):
    service.fetch_and_store("Bangalore")
    clock.advance(timedelta(minutes=5))

    second = service.fetch_and_store("Bangalore")

    assert second.created is True
    assert provider.get_current.call_count == 2
    assert provider.resolve_city.call_count == 1  # location is already known
    assert len(repository.readings) == 2


def test_force_refresh_bypasses_the_cache(service, provider, repository):
    service.fetch_and_store("Bangalore")

    result = service.fetch_and_store("Bangalore", force_refresh=True)

    assert result.created is True
    assert provider.get_current.call_count == 2
    assert len(repository.readings) == 2


def test_city_lookup_ignores_case_whitespace_and_accents(service, provider):
    service.fetch_and_store("Bangalore")

    result = service.fetch_and_store("  BANGALORE ")

    assert result.created is False
    assert provider.resolve_city.call_count == 1


def test_user_alias_resolving_to_known_location_reuses_it(service, provider, repository, clock):
    """'Bangalore' geocodes to the already-stored 'Bengaluru': one location only."""
    provider.resolve_city.return_value = make_geo("Bengaluru", "India", 12.97, 77.59, "Asia/Kolkata")
    service.fetch_and_store("Bengaluru")

    result = service.fetch_and_store("Bangalore")  # alias unknown -> one geocoding call

    assert result.created is False  # fresh reading of the same location
    assert len(repository.locations) == 1
    assert provider.get_current.call_count == 1
    # ...and the new alias is remembered, so no further geocoding is needed
    service.fetch_and_store("bangalore")
    assert provider.resolve_city.call_count == 2


# --- queries ----------------------------------------------------------------


def test_get_readings_returns_most_recent_first(service, provider, clock):
    provider.get_current.side_effect = [
        make_conditions(temperature=10.0),
        make_conditions(temperature=11.0),
        make_conditions(temperature=12.0),
    ]
    for _ in range(3):
        service.fetch_and_store("Bangalore", force_refresh=True)
        clock.advance(timedelta(minutes=10))

    readings = service.get_readings("Bangalore")

    assert [r.temperature for r in readings] == [12.0, 11.0, 10.0]


def test_get_readings_for_unknown_city_is_empty(service):
    assert service.get_readings("Nowhere") == []


def test_get_latest_returns_the_newest_reading(service, provider, clock):
    provider.get_current.side_effect = [
        make_conditions(temperature=10.0),
        make_conditions(temperature=15.0),
    ]
    service.fetch_and_store("Bangalore")
    clock.advance(timedelta(minutes=10))
    service.fetch_and_store("Bangalore")

    assert service.get_latest("bangalore").temperature == 15.0


def test_get_latest_without_readings_raises(service):
    with pytest.raises(NoReadingsFoundError):
        service.get_latest("Nowhere")
