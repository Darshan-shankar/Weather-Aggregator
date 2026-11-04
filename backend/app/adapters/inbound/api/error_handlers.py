"""Translate domain errors into HTTP responses (the only place that knows both)."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.domain.exceptions import (
    CityNotFoundError,
    NoReadingsFoundError,
    WeatherProviderError,
)


def register_error_handlers(app: FastAPI) -> None:
    def respond(status: int):
        def handler(_: Request, exc: Exception) -> JSONResponse:
            return JSONResponse(status_code=status, content={"detail": str(exc)})

        return handler

    app.add_exception_handler(CityNotFoundError, respond(404))
    app.add_exception_handler(NoReadingsFoundError, respond(404))
    app.add_exception_handler(WeatherProviderError, respond(502))
