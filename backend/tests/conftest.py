import pytest

from tests.support.postgres import PostgresDatabase


@pytest.fixture(scope="session")
def database():
    db = PostgresDatabase().start()
    yield db
    db.stop()


@pytest.fixture
def clean_database(database):
    database.truncate()
    return database
