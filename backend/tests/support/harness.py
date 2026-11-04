"""Full-application harness shared by the component tests and the Behave BDD suite.

It wires the *real* FastAPI app to the *real* PostgreSQL and
replaces only the outermost boundary - Open-Meteo - with an HTTP stub. Behave
reuses this exact class, so there is no second copy of the infrastructure.
"""

from __future__ import annotations

import responses
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.support.fakes import T0, MutableClock
from tests.support.open_meteo_stub import OpenMeteoStub
from tests.support.postgres import PostgresDatabase


class AppHarness:
    def __init__(self, database: PostgresDatabase) -> None:
        self.database = database

    def start(self) -> "AppHarness":
        """Build the real application once (expensive part)."""
        self.clock = MutableClock()
        settings = Settings(database_url=self.database.url, cache_max_age_seconds=300)
        self.app = create_app(settings, clock=self.clock, sleep=lambda _: None)
        self.client = TestClient(self.app)
        self._rsps: responses.RequestsMock | None = None
        return self

    def begin(self) -> "AppHarness":
        """Per test/scenario: clean DB, reset clock, activate a fresh Open-Meteo stub.

        The HTTP stub is only active between begin() and end() so that it can
        never intercept unrelated traffic (e.g. the Pact mock service).
        """
        self.database.truncate()
        self.clock.set(T0)
        self._rsps = responses.RequestsMock(assert_all_requests_are_fired=False)
        self._rsps.start()
        self.open_meteo = OpenMeteoStub(self._rsps)
        return self

    def end(self) -> None:
        if self._rsps is not None:
            self._rsps.stop()
            self._rsps.reset()
            self._rsps = None

    def stop(self) -> None:
        self.end()
        self.client.close()
        self.app.state.engine.dispose()

    @property
    def external_calls(self) -> int:
        return len(self._rsps.calls)
