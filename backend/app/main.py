"""Composition root: the only place where ports are wired to concrete adapters."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Callable

import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.adapters.inbound.api.error_handlers import register_error_handlers
from app.adapters.inbound.api.routes import router
from app.adapters.outbound.clock import SystemClock
from app.adapters.outbound.open_meteo.adapter import OpenMeteoAdapter
from app.adapters.outbound.open_meteo.http_client import HttpClientConfig
from app.adapters.outbound.persistence.repository import PostgresWeatherRepository
from app.config import Settings
from app.domain.freshness import FreshnessPolicy
from app.ports.outbound import Clock
from app.services.weather_service import WeatherService


def create_app(
    settings: Settings | None = None,
    *,
    clock: Clock | None = None,
    sleep: Callable[[float], None] | None = None,
) -> FastAPI:
    """Build the application. `clock` and `sleep` are injectable for tests."""
    settings = settings or Settings()

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    repository = PostgresWeatherRepository(sessionmaker(engine, expire_on_commit=False))
    provider = OpenMeteoAdapter(
        session=requests.Session(),
        config=HttpClientConfig(
            connect_timeout=settings.http_connect_timeout,
            read_timeout=settings.http_read_timeout,
            max_attempts=settings.http_max_attempts,
            backoff_base=settings.http_backoff_base,
        ),
        sleep=sleep,
    )
    service = WeatherService(
        provider=provider,
        repository=repository,
        clock=clock or SystemClock(),
        freshness=FreshnessPolicy(max_age=settings.cache_max_age),
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield
        engine.dispose()

    app = FastAPI(title="Weather Aggregator", version="0.1.0", lifespan=lifespan)
    app.state.weather_use_case = service
    app.state.engine = engine
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )
    register_error_handlers(app)
    app.include_router(router)
    return app
