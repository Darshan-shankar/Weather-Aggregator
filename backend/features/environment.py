"""Behave hooks. Reuses the pytest harness: same PostgreSQL,
same Open-Meteo stub, same wiring of the real application."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tests.support.harness import AppHarness  # noqa: E402
from tests.support.postgres import PostgresDatabase  # noqa: E402


def before_all(context):
    context.database = PostgresDatabase().start()
    context.harness = AppHarness(context.database).start()


def before_scenario(context, scenario):
    context.harness.begin()
    context.coordinates = {}  # city -> (lat, lon) as announced by the Background
    context.response = None
    context.external_calls_after_first_fetch = None


def after_scenario(context, scenario):
    context.harness.end()


def after_all(context):
    context.harness.stop()
    context.database.stop()
