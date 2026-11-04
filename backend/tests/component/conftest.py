import pytest

from tests.support.harness import AppHarness


@pytest.fixture(scope="session")
def _harness(database):
    harness = AppHarness(database).start()
    yield harness
    harness.stop()


@pytest.fixture
def harness(_harness):
    _harness.begin()
    yield _harness
    _harness.end()
