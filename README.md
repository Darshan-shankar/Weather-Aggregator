# Weather Aggregator

Fetches current weather from [Open-Meteo](https://open-meteo.com), stores each
reading in PostgreSQL and exposes a small REST API plus a Next.js UI.
Backend: Python 3.12 / FastAPI, structured as **Hexagonal Architecture (Ports & Adapters)**.

## Run it

Run the following commands in **Windows Command Prompt**. PostgreSQL must be
installed and running locally.

```cmd
REM Backend
cd d:\projects\weather-aggregator\weather-aggregator\backend
python -m venv .venv
.venv\Scripts\activate.bat

python -m pip install -e ".[test]"
copy .env.example .env
REM Set DATABASE_URL in .env for your local PostgreSQL instance.
python -m alembic upgrade head
python -m uvicorn app.main:create_app --factory --reload
```

Open a second Command Prompt window for the frontend:

```cmd
cd d:\projects\weather-aggregator\weather-aggregator\frontend
npm ci
npm run dev
```

The frontend is available at `http://localhost:3000` and the backend at
`http://localhost:8000/docs`.

## API

| Method | Endpoint | Behaviour |
|---|---|---|
| POST | `/weather/fetch?city=X` (or JSON `{"city": "X"}`) | **201** new reading stored · **200** a fresh reading (< 5 min) was reused · 404 unknown city · 502 provider failure · 422 city missing |
| GET | `/weather/{city}` | All stored readings, most recent first (`[]` if none) |
| GET | `/weather/{city}/latest` | Most recent reading (404 if none) |
| GET | `/health` | Liveness |
| GET | `/ready` | Readiness (checks the database) |

`POST /weather/fetch?force_refresh=true` bypasses the freshness window.

## Tests

DB-backed suites require a PostgreSQL database. Set the connection URL in
Command Prompt before running backend tests:

```cmd
set TEST_DATABASE_URL=postgresql+psycopg://weather:weather@localhost:5432/test_db
```

From the `backend` directory, run:

| Suite | Command | What it covers |
|---|---|---|
| All Python tests | `python -m pytest` | Unit, adapter, contract, integration, and component tests |
| Unit | `python -m pytest -m unit` | `WeatherService` with a stubbed provider and an in-memory repository; no I/O |
| Adapter | `python -m pytest -m adapter` | `OpenMeteoAdapter` vs. stubbed HTTP (`responses`): mapping, timeouts, retries, error translation |
| Contract | `python -m pytest -m contract` | Pact consumer test for `OpenMeteoAdapter` and provider verification against a local stub |
| Integration | `python -m pytest -m integration` | `PostgresWeatherRepository` against a real PostgreSQL, including the Alembic migration |
| Component | `python -m pytest -m component` | Full FastAPI app + real PostgreSQL, Open-Meteo stubbed with `responses` |
| BDD | `python -m behave --no-color` | Behave scenarios against the shared test harness |

From the `frontend` directory, run:

```cmd
npm test
npm run typecheck
```

The schema is created by the real Alembic migrations.

## Architecture

```
FastAPI routes ──► WeatherUseCase (inbound port)
                        │
                  WeatherService  ── FreshnessPolicy, Clock
                  ┌─────┴──────────────┐
      WeatherProviderPort      WeatherRepositoryPort   (outbound ports)
                  │                    │
         OpenMeteoAdapter     PostgresWeatherRepository   (outbound adapters)
```

```
backend/app/
  domain/      models, exceptions, normalisation, freshness  (pure Python)
  ports/       inbound.py, outbound.py                       (abstract interfaces)
  services/    weather_service.py                            (use-case implementation)
  adapters/
    inbound/api/        FastAPI routes, schemas, error → HTTP mapping
    outbound/open_meteo/ HTTP adapter, retry/timeout client, WMO table
    outbound/persistence/ SQLAlchemy ORM + repository
  main.py      composition root (the only place that wires adapters to ports)
```

**Boundaries.** Dependencies point inward only. The domain and service import no
FastAPI, SQLAlchemy or `requests`. Infrastructure exceptions are translated at the
adapter boundary (`requests.Timeout` → `WeatherProviderError`) and domain errors
are translated to HTTP status codes only in the inbound adapter.

**Caching.** `WeatherService` serves the latest stored reading if it is younger
than `CACHE_MAX_AGE_SECONDS` (default 300), so repeat requests cost zero
external calls. The freshness decision is a pure domain object; Redis could be
added behind a new port without touching it.

**Data model.** `locations` (unique on name + country + coordinates),
`location_aliases` (normalised user input → location) and `weather_readings`
(index on `location_id, fetched_at`). Readings store both `observed_at` (from
Open-Meteo) and `fetched_at` (ours), plus explicit units and the WMO code.

## Decisions and trade-offs

- **Humidity needs the `current=` parameter, not `current_weather=true`.**
  The brief mentions only `current_weather`, which has no humidity. The adapter
  requests `temperature_2m, relative_humidity_2m, wind_speed_10m, weather_code`
  via `current=`. Still current conditions only (no forecast/hourly). Humidity is
  nullable if you prefer to drop it.
- **Aliases instead of "city name = key".** A user typing "Bangalore" gets
  "Bengaluru" back; both names (case- and accent-insensitive) find the same
  location. Trade-off: if two *different* places share a typed name, the first
  one stored owns that alias (e.g. "Springfield"). Geocoding always takes the
  first Open-Meteo result (`count=1`), as in the brief.
- **WMO code → text lives in the Open-Meteo adapter**, since weather codes are
  a provider detail; the domain only sees a description.
- **Synchronous FastAPI + `requests`**: simple, and works directly with `responses`.
  Retries are an explicit loop (not `urllib3.Retry`) so that backoff is
  unit-testable and invisible to the HTTP-mocking library.
- **Pact limitation.** Open-Meteo is third-party, so the provider verification
  replays our Pact against a local stub: it proves the stub and the adapter agree
  on the contract, **not** that the real Open-Meteo still behaves that way. That
  gap is covered by realistic fixtures in the adapter tests. A frontend ↔ FastAPI
  Pact (where the provider *is* verifiable) is a worthwhile next step and is not
  implemented.
- **Tests share one harness.** `tests/support/harness.py` (real app + real
  PostgreSQL + Open-Meteo stub) is used by both the component tests and Behave.
  The HTTP stub is only active within a test/scenario, so it can't intercept
  unrelated traffic.
- **Not covered**: authentication, rate limiting of our own API, and data retention.
