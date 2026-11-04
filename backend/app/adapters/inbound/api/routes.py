from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, Response
from sqlalchemy import text

from app.adapters.inbound.api.schemas import (
    ErrorResponse,
    FetchRequest,
    WeatherReadingResponse,
)
from app.ports.inbound import WeatherUseCase

router = APIRouter()


def get_use_case(request: Request) -> WeatherUseCase:
    return request.app.state.weather_use_case


@router.post(
    "/weather/fetch",
    response_model=WeatherReadingResponse,
    status_code=201,
    tags=["weather"],
    summary="Fetch current weather for a city and store it",
    responses={
        200: {"model": WeatherReadingResponse, "description": "Fresh cached reading returned"},
        404: {"model": ErrorResponse, "description": "City not found"},
        422: {"model": ErrorResponse, "description": "City missing"},
        502: {"model": ErrorResponse, "description": "Weather provider failure"},
    },
)
def fetch_weather(
    response: Response,
    city: str | None = Query(default=None, description="City name"),
    body: FetchRequest | None = Body(default=None),
    force_refresh: bool = Query(default=False, description="Bypass the freshness window"),
    use_case: WeatherUseCase = Depends(get_use_case),
) -> WeatherReadingResponse:
    name = (city or (body.city if body else "") or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="city is required")
    result = use_case.fetch_and_store(name, force_refresh=force_refresh)
    response.status_code = 201 if result.created else 200
    return WeatherReadingResponse.from_domain(result.reading)


@router.get(
    "/weather/{city}",
    response_model=list[WeatherReadingResponse],
    tags=["weather"],
    summary="All stored readings for a city, most recent first",
)
def list_readings(
    city: str, use_case: WeatherUseCase = Depends(get_use_case)
) -> list[WeatherReadingResponse]:
    return [WeatherReadingResponse.from_domain(r) for r in use_case.get_readings(city)]


@router.get(
    "/weather/{city}/latest",
    response_model=WeatherReadingResponse,
    tags=["weather"],
    summary="Most recent stored reading for a city",
    responses={404: {"model": ErrorResponse}},
)
def latest_reading(
    city: str, use_case: WeatherUseCase = Depends(get_use_case)
) -> WeatherReadingResponse:
    return WeatherReadingResponse.from_domain(use_case.get_latest(city))


@router.get("/health", tags=["ops"], summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", tags=["ops"], summary="Readiness probe (checks the database)")
def ready(request: Request, response: Response) -> dict[str, str]:
    try:
        with request.app.state.engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001 - any DB failure means "not ready"
        response.status_code = 503
        return {"status": "unavailable"}
    return {"status": "ready"}
