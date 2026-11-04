"""Real PostgreSQL for tests.

TEST_DATABASE_URL must point to an available PostgreSQL database. The schema
is created by running the real Alembic migrations, so the migration itself
is under test too.
"""

from __future__ import annotations

import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

BACKEND_DIR = Path(__file__).resolve().parents[2]
TABLES = "weather_readings, location_aliases, locations"


def run_migrations(url: str) -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    command.upgrade(cfg, "head")


class PostgresDatabase:
    def __init__(self) -> None:
        self.url = ""
        self._engine = None

    def start(self) -> "PostgresDatabase":
        override = os.environ.get("TEST_DATABASE_URL")
        if override:
            self.url = override
        else:
            raise RuntimeError(
                "TEST_DATABASE_URL is required for database-backed tests"
            )
        run_migrations(self.url)
        self._engine = create_engine(self.url, pool_pre_ping=True)
        return self

    @property
    def session_factory(self) -> sessionmaker[Session]:
        return sessionmaker(self._engine, expire_on_commit=False)

    def truncate(self) -> None:
        with self._engine.begin() as conn:
            conn.execute(text(f"TRUNCATE {TABLES} CASCADE"))

    def scalar(self, sql: str):
        with self._engine.connect() as conn:
            return conn.execute(text(sql)).scalar()

    def stop(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
