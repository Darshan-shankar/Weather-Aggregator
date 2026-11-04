"""Provider verification: replay the generated Pact against a local stub.

IMPORTANT LIMITATION: Open-Meteo is a third-party service whose real
implementation we cannot verify. This test proves our stub honours the same
contract our adapter was written against (and keeps the Pact file replayable);
it does not prove the real Open-Meteo still behaves this way. The adapter
tests with realistic fixtures and the stub-based component/BDD suites cover
the rest.
"""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

import pytest
from pact import Verifier

from tests.contract.conftest import PACT_FILE, PROVIDER
from tests.support.open_meteo_stub import forecast_payload, geocoding_payload

pytestmark = pytest.mark.contract


class OpenMeteoStubHandler(BaseHTTPRequestHandler):
    state = "default"

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):  # Pact provider-state setup callback
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length) or b"{}")
        OpenMeteoStubHandler.state = body.get("state", "default")
        self._send(200, {})

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/v1/search":
            if OpenMeteoStubHandler.state.startswith("no city matches"):
                self._send(200, {"generationtime_ms": 0.4})
            else:
                self._send(200, geocoding_payload())
        elif path == "/v1/forecast":
            self._send(200, forecast_payload())
        else:
            self._send(404, {"error": True})

    def log_message(self, *args):  # keep test output quiet
        pass


@pytest.fixture
def stub_provider():
    server = ThreadingHTTPServer(("127.0.0.1", 0), OpenMeteoStubHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    thread.join()


def test_stub_provider_honours_the_consumer_contract(stub_provider):
    assert PACT_FILE.exists(), "run the consumer tests first to generate the pact"

    verifier = Verifier(provider=PROVIDER, provider_base_url=stub_provider)
    exit_code, _logs = verifier.verify_pacts(
        str(PACT_FILE),
        provider_states_setup_url=f"{stub_provider}/_pact/provider-states",
    )

    assert exit_code == 0
