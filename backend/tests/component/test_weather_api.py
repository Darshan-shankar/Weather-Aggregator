"""Component tests: HTTP in -> real app -> real PostgreSQL -> HTTP out.

Only Open-Meteo is stubbed (`responses`); everything else is the real thing.
"""

from datetime import timedelta

import pytest

pytestmark = pytest.mark.component

BANGALORE = {"latitude": 12.97, "longitude": 77.59}


def stub_bangalore(harness, **conditions):
    harness.open_meteo.known_city("Bangalore", **BANGALORE, country="India",
                                  timezone="Asia/Kolkata")
    harness.open_meteo.weather_at(**BANGALORE, **conditions)


# --- POST /weather/fetch -------------------------------------------------------------


def test_fetch_stores_the_reading_and_returns_it(harness):
    stub_bangalore(harness, temperature=22.4, wind_speed=14.2, weather_code=61, humidity=70)

    response = harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    assert response.status_code == 201
    body = response.json()
    assert body["city"] == "Bangalore" and body["country"] == "India"
    assert body["temperature"] == 22.4 and body["temperature_unit"] == "celsius"
    assert body["wind_speed"] == 14.2 and body["wind_speed_unit"] == "kmh"
    assert body["weather_description"] == "Rain: slight" and body["weather_code"] == 61
    assert body["humidity"] == 70 and body["timezone"] == "Asia/Kolkata"
    assert body["observed_at"] == "2026-11-04T10:00:00Z"
    assert body["fetched_at"] == "2026-11-04T10:00:00Z"
    # ...and it really is in the database
    assert harness.database.scalar("SELECT count(*) FROM weather_readings") == 1
    assert harness.database.scalar("SELECT temperature FROM weather_readings") == 22.4


def test_fetch_accepts_a_json_body_too(harness):
    stub_bangalore(harness)

    response = harness.client.post("/weather/fetch", json={"city": "Bangalore"})

    assert response.status_code == 201


def test_fetch_without_a_city_is_rejected(harness):
    response = harness.client.post("/weather/fetch")

    assert response.status_code == 422
    assert harness.external_calls == 0


def test_repeat_fetch_within_the_window_is_served_from_the_database(harness):
    stub_bangalore(harness)
    first = harness.client.post("/weather/fetch", params={"city": "Bangalore"})
    calls_after_first = harness.external_calls

    harness.clock.advance(timedelta(minutes=2))
    second = harness.client.post("/weather/fetch", params={"city": "bangalore"})

    assert (first.status_code, second.status_code) == (201, 200)
    assert second.json()["id"] == first.json()["id"]
    assert harness.external_calls == calls_after_first == 2  # geocoding + weather, once
    assert harness.database.scalar("SELECT count(*) FROM weather_readings") == 1


def test_fetch_after_the_window_creates_a_new_reading(harness):
    stub_bangalore(harness, temperature=10.0)
    harness.client.post("/weather/fetch", params={"city": "Bangalore"})
    harness.open_meteo.weather_at(**BANGALORE, temperature=12.5, time="2026-11-04T10:15")

    harness.clock.advance(timedelta(minutes=15))
    response = harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    assert response.status_code == 201
    assert response.json()["temperature"] == 12.5
    assert harness.database.scalar("SELECT count(*) FROM weather_readings") == 2
    assert harness.database.scalar("SELECT count(*) FROM locations") == 1


def test_force_refresh_skips_the_cache(harness):
    stub_bangalore(harness)
    harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    response = harness.client.post(
        "/weather/fetch", params={"city": "Bangalore", "force_refresh": "true"}
    )

    assert response.status_code == 201
    assert harness.database.scalar("SELECT count(*) FROM weather_readings") == 2


def test_unknown_city_returns_404_and_stores_nothing(harness):
    harness.open_meteo.unknown_city("Atlantis")

    response = harness.client.post("/weather/fetch", params={"city": "Atlantis"})

    assert response.status_code == 404
    assert "Atlantis" in response.json()["detail"]
    assert harness.database.scalar("SELECT count(*) FROM locations") == 0


def test_provider_outage_returns_502_and_stores_no_reading(harness):
    harness.open_meteo.known_city("Bangalore", **BANGALORE)
    harness.open_meteo.provider_down()  # 503 on the forecast endpoint

    response = harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    assert response.status_code == 502
    assert harness.database.scalar("SELECT count(*) FROM weather_readings") == 0


def test_provider_timeout_returns_502(harness):
    harness.open_meteo.provider_times_out()

    response = harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    assert response.status_code == 502
    assert "timed out" in response.json()["detail"]


def test_a_different_spelling_resolves_to_the_same_stored_location(harness):
    harness.open_meteo.known_city("Bangalore", name="Bengaluru", country="India",
                                  latitude=12.97194, longitude=77.59369, timezone="Asia/Kolkata")
    harness.open_meteo.weather_at(12.97194, 77.59369, temperature=28.5, weather_code=2)

    created = harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    assert created.json()["city"] == "Bengaluru"
    # both the typed alias and the canonical name now find the reading
    for name in ("Bangalore", "bangalore", "Bengaluru"):
        assert len(harness.client.get(f"/weather/{name}").json()) == 1


# --- GET /weather/{city} and /latest ---------------------------------------------------


def test_list_returns_readings_most_recent_first(harness):
    stub_bangalore(harness, temperature=10.0, time="2026-11-04T10:00")
    harness.open_meteo.weather_at(**BANGALORE, temperature=11.0, time="2026-11-04T10:10")
    harness.open_meteo.weather_at(**BANGALORE, temperature=12.0, time="2026-11-04T10:20")
    for _ in range(3):
        harness.client.post("/weather/fetch", params={"city": "Bangalore"})
        harness.clock.advance(timedelta(minutes=10))

    response = harness.client.get("/weather/Bangalore")

    assert response.status_code == 200
    assert [r["temperature"] for r in response.json()] == [12.0, 11.0, 10.0]


def test_list_for_a_city_without_readings_is_an_empty_list(harness):
    response = harness.client.get("/weather/Nowhere")

    assert response.status_code == 200 and response.json() == []


def test_latest_returns_only_the_newest_reading(harness):
    stub_bangalore(harness, temperature=10.0)
    harness.open_meteo.weather_at(**BANGALORE, temperature=14.0)
    harness.client.post("/weather/fetch", params={"city": "Bangalore"})
    harness.clock.advance(timedelta(minutes=10))
    harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    response = harness.client.get("/weather/Bangalore/latest")

    assert response.status_code == 200 and response.json()["temperature"] == 14.0


def test_latest_for_a_city_without_readings_is_404(harness):
    assert harness.client.get("/weather/Nowhere/latest").status_code == 404


def test_lookup_ignores_accents_and_case(harness):
    stub_bangalore(harness)
    harness.client.post("/weather/fetch", params={"city": "Bangalore"})

    response = harness.client.get("/weather/TIMIȘOARA")

    assert len(response.json()) == 1


# --- ops ------------------------------------------------------------------------------


def test_health_and_readiness(harness):
    assert harness.client.get("/health").json() == {"status": "ok"}
    ready = harness.client.get("/ready")
    assert ready.status_code == 200 and ready.json() == {"status": "ready"}
