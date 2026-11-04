from datetime import timedelta

from behave import given, then, when


# --- Given -----------------------------------------------------------------------


@given('Open-Meteo knows the city "{city}" at latitude {lat:f} and longitude {lon:f}')
def step_known_city(context, city, lat, lon):
    context.coordinates[city] = (lat, lon)
    context.harness.open_meteo.known_city(city, latitude=lat, longitude=lon)


@given('Open-Meteo does not know the city "{city}"')
def step_unknown_city(context, city):
    context.harness.open_meteo.unknown_city(city)


@given(
    'Open-Meteo reports {temperature:f} degrees, wind {wind:f} km/h '
    'and weather code {code:d} for "{city}"'
)
def step_reports_weather(context, temperature, wind, code, city):
    lat, lon = context.coordinates[city]
    context.harness.open_meteo.weather_at(
        lat, lon, temperature=temperature, wind_speed=wind, weather_code=code
    )


@given("Open-Meteo is unavailable")
def step_provider_down(context):
    context.harness.open_meteo.provider_down()


# --- When ------------------------------------------------------------------------


@when('I fetch the weather for "{city}"')
def step_fetch(context, city):
    context.response = context.harness.client.post("/weather/fetch", params={"city": city})
    if context.external_calls_after_first_fetch is None:
        context.external_calls_after_first_fetch = context.harness.external_calls


@when("{minutes:d} minutes pass")
def step_time_passes(context, minutes):
    context.harness.clock.advance(timedelta(minutes=minutes))


@when('I request the stored readings for "{city}"')
def step_list(context, city):
    context.response = context.harness.client.get(f"/weather/{city}")


@when('I request the latest reading for "{city}"')
def step_latest(context, city):
    context.response = context.harness.client.get(f"/weather/{city}/latest")


# --- Then ------------------------------------------------------------------------


@then("the response status is {status:d}")
def step_status(context, status):
    assert context.response.status_code == status, (
        f"expected {status}, got {context.response.status_code}: {context.response.text}"
    )


@then(
    'the reading shows {temperature:f} degrees and wind {wind:f} km/h described as "{description}"'
)
def step_reading_shows(context, temperature, wind, description):
    body = context.response.json()
    assert body["temperature"] == temperature
    assert body["wind_speed"] == wind
    assert body["weather_description"] == description


@then('{count:d} reading is stored for "{city}"')
@then('{count:d} readings are stored for "{city}"')
def step_stored_count(context, count, city):
    stored = context.harness.client.get(f"/weather/{city}").json()
    assert len(stored) == count, f"expected {count} stored readings, found {len(stored)}"


@then("Open-Meteo was only contacted for the first fetch")
def step_no_extra_calls(context):
    assert context.harness.external_calls == context.external_calls_after_first_fetch


@then("the readings have temperatures {first:f}, {second:f} in that order")
def step_order(context, first, second):
    assert [r["temperature"] for r in context.response.json()] == [first, second]
