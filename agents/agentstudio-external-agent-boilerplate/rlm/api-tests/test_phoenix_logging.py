"""
Test that verifies messages are logged as sessions in local Phoenix.

Requires:
 - Agent running with ICA_OBSERVABILITY=true and PHOENIX_COLLECTOR_ENDPOINT set to local Phoenix.
 - Phoenix running locally (e.g. via `make dev` which calls `ensure-local-phoenix`).

The test is skipped when Phoenix is not accessible so it does not block CI
environments where a local Phoenix instance is not available.
"""

import os
import time
import httpx
import pytest

BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")
RPC_PATH = os.getenv("RPC_PATH", "/v1/rpc")
PHOENIX_BASE_URL = os.getenv("PHOENIX_BASE_URL", "http://localhost:6006")
PHOENIX_PROJECT_NAME = os.getenv("ICA_APP_ID", "f16c63ed-21c5-4e21-9b4f-fa0053e461d4")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
_AUTH_HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
_OTEL_EXPORT_WAIT_SECONDS = float(os.getenv("PHOENIX_EXPORT_WAIT", "5"))


def _phoenix_client() -> httpx.Client:
    return httpx.Client(base_url=PHOENIX_BASE_URL, timeout=10.0)


def _send_request(text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "message/send",
        "id": "test-phoenix-1",
        "params": {
            "message": {
                "messageId": "msg-phoenix-001",
                "role": "user",
                "kind": "message",
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }


def _get_span_count(phoenix: httpx.Client, project_name: str) -> int:
    """Return the number of spans currently in the Phoenix project."""
    resp = phoenix.get(f"/v1/projects/{project_name}/spans", params={"limit": 1000})
    if resp.status_code == 404:
        return 0
    resp.raise_for_status()
    return len(resp.json().get("data", []))


@pytest.fixture(scope="module")
def phoenix_client():
    """Yield an httpx client for Phoenix; skip the module if Phoenix is not reachable."""
    try:
        client = _phoenix_client()
        resp = client.get("/v1/projects")
        if resp.status_code != 200:
            pytest.skip(f"Phoenix not accessible at {PHOENIX_BASE_URL} (status {resp.status_code})")
    except Exception as exc:
        pytest.skip(f"Phoenix not accessible at {PHOENIX_BASE_URL}: {exc}")
    yield client
    client.close()


class TestPhoenixSessionLogging:
    """Verify that a message/send request creates a span in local Phoenix."""

    def test_message_creates_span_in_phoenix(self, phoenix_client, auth_headers):
        if not PHOENIX_PROJECT_NAME:
            pytest.skip("PHOENIX_PROJECT_NAME / ICA_APP_ID not set – cannot determine Phoenix project")

        span_count_before = _get_span_count(phoenix_client, PHOENIX_PROJECT_NAME)

        with httpx.Client(base_url=BASE_URL, timeout=30.0, headers=auth_headers) as agent:
            response = agent.post(RPC_PATH, json=_send_request("Hello"))
        assert response.status_code == 200, f"Agent returned {response.status_code}: {response.text}"

        # Allow time for the OTEL batch exporter to flush spans to Phoenix.
        time.sleep(_OTEL_EXPORT_WAIT_SECONDS)

        span_count_after = _get_span_count(phoenix_client, PHOENIX_PROJECT_NAME)
        assert span_count_after > span_count_before, (
            f"Expected new spans in Phoenix project '{PHOENIX_PROJECT_NAME}' after sending a message, "
            f"but span count stayed at {span_count_before}. "
            "Check that ICA_OBSERVABILITY=true and PHOENIX_COLLECTOR_ENDPOINT is set correctly."
        )
