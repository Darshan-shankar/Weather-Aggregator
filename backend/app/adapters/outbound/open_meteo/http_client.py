"""Resilient JSON-over-HTTP helper: timeouts, bounded retries, error translation.

Infrastructure exceptions (requests.*) never leave this module: they are
translated into the domain's WeatherProviderError.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Callable

import requests

from app.domain.exceptions import WeatherProviderError

RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


@dataclass(frozen=True)
class HttpClientConfig:
    connect_timeout: float = 3.0
    read_timeout: float = 10.0
    max_attempts: int = 3
    backoff_base: float = 0.5  # seconds; doubles on every retry
    backoff_max: float = 8.0


@dataclass(frozen=True)
class _Outcome:
    payload: Any = None
    error: WeatherProviderError | None = None
    retry_delay: float | None = None  # None => not retryable


class ResilientJsonClient:
    def __init__(
        self,
        session: requests.Session,
        config: HttpClientConfig | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._session = session
        self._config = config or HttpClientConfig()
        self._sleep = sleep

    def get_json(self, url: str, params: dict[str, Any]) -> Any:
        cfg = self._config
        for attempt in range(1, cfg.max_attempts + 1):
            outcome = self._attempt(url, params, attempt)
            if outcome.error is None:
                return outcome.payload
            if outcome.retry_delay is None or attempt == cfg.max_attempts:
                raise outcome.error
            self._sleep(outcome.retry_delay)
        raise AssertionError("unreachable")  # pragma: no cover

    def _attempt(self, url: str, params: dict[str, Any], attempt: int) -> _Outcome:
        cfg = self._config
        backoff = min(cfg.backoff_base * 2 ** (attempt - 1), cfg.backoff_max)
        try:
            response = self._session.get(
                url, params=params, timeout=(cfg.connect_timeout, cfg.read_timeout)
            )
        except requests.Timeout as exc:
            return _Outcome(error=self._error("Weather provider timed out", exc), retry_delay=backoff)
        except requests.RequestException as exc:
            return _Outcome(error=self._error("Weather provider unavailable", exc), retry_delay=backoff)

        status = response.status_code
        if status in RETRYABLE_STATUS:
            hinted = self._retry_after(response) if status == 429 else None
            delay = min(hinted if hinted is not None else backoff, cfg.backoff_max)
            return _Outcome(
                error=WeatherProviderError(f"Weather provider returned HTTP {status}"),
                retry_delay=delay,
            )
        if status >= 400:
            return _Outcome(
                error=WeatherProviderError(f"Weather provider rejected request (HTTP {status})")
            )
        try:
            return _Outcome(payload=response.json())
        except ValueError as exc:
            return _Outcome(error=self._error("Weather provider returned invalid JSON", exc))

    @staticmethod
    def _error(message: str, cause: Exception) -> WeatherProviderError:
        err = WeatherProviderError(message)
        err.__cause__ = cause
        return err

    @staticmethod
    def _retry_after(response: requests.Response) -> float | None:
        raw = response.headers.get("Retry-After")
        try:
            return max(0.0, float(raw)) if raw is not None else None
        except ValueError:
            return None
