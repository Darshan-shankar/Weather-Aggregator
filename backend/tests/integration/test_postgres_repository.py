"""PostgresWeatherRepository end-to-end against a real PostgreSQL (no mocks)."""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from app.adapters.outbound.persistence.repository import PostgresWeatherRepository
from app.domain.models import Location, WeatherReading
from tests.support.fakes import T0, make_conditions, make_geo

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(clean_database):
    return PostgresWeatherRepository(clean_database.session_factory)


def a_location(**overrides) -> Location:
    return Location.from_geo(make_geo(**overrides), id=uuid4())


def a_reading(location: Location, minutes: int = 0, **conditions) -> WeatherReading:
    return WeatherReading.create(
        location,
        make_conditions(**conditions),
        fetched_at=T0 + timedelta(minutes=minutes),
    )


# --- locations -----------------------------------------------------------------


def test_saved_location_is_found_by_alias(repo):
    saved = repo.save_location(a_location(), {"bangalore", "bangalore-alt"})

    assert repo.find_location_by_alias("bangalore") == saved
    assert repo.find_location_by_alias("bangalore-alt") == saved
    assert repo.find_location_by_alias("nowhere") is None


def test_location_round_trips_all_fields(repo):
    original = a_location(name="Bengaluru", country="India", latitude=12.97194,
                          longitude=77.59369, timezone_name="Asia/Kolkata")

    found = repo.save_location(original, {"bengaluru"})

    assert found == original


def test_saving_the_same_place_twice_returns_the_existing_row(repo, clean_database):
    first = repo.save_location(a_location(), {"bangalore"})

    second = repo.save_location(a_location(), {"bangalore", "temeswar"})  # new uuid, same place

    assert second.id == first.id
    assert clean_database.scalar("SELECT count(*) FROM locations") == 1
    assert repo.find_location_by_alias("temeswar") == first  # new alias attached


def test_same_name_in_different_countries_are_distinct_locations(repo):
    us = repo.save_location(a_location(name="Springfield", country="United States",
                                       latitude=39.8, longitude=-89.65), {"springfield-us"})
    ca = repo.save_location(a_location(name="Springfield", country="Canada",
                                       latitude=49.8, longitude=-96.9), {"springfield-ca"})

    assert us.id != ca.id


def test_an_alias_keeps_its_first_owner(repo):
    first = repo.save_location(a_location(name="Springfield", country="United States",
                                          latitude=39.8, longitude=-89.65), {"springfield"})
    repo.save_location(a_location(name="Springfield", country="Canada",
                                  latitude=49.8, longitude=-96.9), {"springfield"})

    assert repo.find_location_by_alias("springfield") == first


# --- readings ----------------------------------------------------------------------


def test_save_reading_and_retrieve_by_location(repo):
    location = repo.save_location(a_location(), {"bangalore"})
    reading = a_reading(location, temperature=21.5, weather_code=61, description="Rain: slight")

    repo.save_reading(reading)

    assert repo.find_readings(location.id) == [reading]


def test_readings_come_back_most_recent_first(repo):
    location = repo.save_location(a_location(), {"bangalore"})
    oldest, middle, newest = (a_reading(location, minutes=m) for m in (0, 10, 20))
    for r in (middle, newest, oldest):  # inserted out of order on purpose
        repo.save_reading(r)

    assert repo.find_readings(location.id) == [newest, middle, oldest]


def test_find_latest_returns_only_the_newest_reading(repo):
    location = repo.save_location(a_location(), {"bangalore"})
    repo.save_reading(a_reading(location, minutes=0, temperature=10.0))
    newest = a_reading(location, minutes=30, temperature=15.0)
    repo.save_reading(newest)

    assert repo.find_latest(location.id) == newest


def test_find_latest_without_readings_is_none(repo):
    location = repo.save_location(a_location(), {"bangalore"})

    assert repo.find_latest(location.id) is None
    assert repo.find_readings(location.id) == []


def test_readings_are_isolated_per_location(repo):
    bangalore = repo.save_location(a_location(), {"bangalore"})
    oslo = repo.save_location(a_location(name="Oslo", country="Norway", latitude=59.9,
                                         longitude=10.75), {"oslo"})
    repo.save_reading(a_reading(bangalore))
    oslo_reading = a_reading(oslo, temperature=-3.0)
    repo.save_reading(oslo_reading)

    assert repo.find_readings(oslo.id) == [oslo_reading]


def test_optional_humidity_and_timezone_aware_timestamps_survive_a_round_trip(repo):
    location = repo.save_location(a_location(), {"bangalore"})
    observed = datetime(2026, 11, 4, 9, 45, tzinfo=timezone.utc)
    reading = a_reading(location, humidity=None, observed_at=observed)

    repo.save_reading(reading)
    stored = repo.find_latest(location.id)

    assert stored.humidity is None
    assert stored.observed_at == observed and stored.observed_at.utcoffset() == timedelta(0)
    assert stored.fetched_at == reading.fetched_at
