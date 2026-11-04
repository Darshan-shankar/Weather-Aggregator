from pathlib import Path

import pytest
from pact import Consumer, Provider

PACT_DIR = Path(__file__).resolve().parents[2] / "pacts"
CONSUMER = "weather-aggregator"
PROVIDER = "open-meteo"
PACT_FILE = PACT_DIR / f"{CONSUMER}-{PROVIDER}.json"
PACT_PORT = 1235


@pytest.fixture(scope="session")
def pact():
    """Pact mock service. Running the consumer tests (re)generates pacts/*.json."""
    PACT_DIR.mkdir(exist_ok=True)
    pact = Consumer(CONSUMER).has_pact_with(
        Provider(PROVIDER),
        host_name="localhost",
        port=PACT_PORT,
        pact_dir=str(PACT_DIR),
        file_write_mode="overwrite",
    )
    pact.start_service()
    yield pact
    pact.stop_service()
