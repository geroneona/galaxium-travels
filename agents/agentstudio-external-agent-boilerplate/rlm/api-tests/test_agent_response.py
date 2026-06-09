"""
SSE streaming test — verifies the agent responds without errors to a message.

Sends a ``message/stream`` JSON-RPC request and verifies:
1. Server responds with ``text/event-stream`` content type.
2. An ``artifact-update`` event carrying the final text is received.
3. A final ``status-update`` event with state ``completed`` arrives.
"""

import json
import os

import httpx
import pytest

BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")
RPC_PATH = os.getenv("RPC_PATH", "/v1/rpc")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
_AUTH_HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}
_STREAM_TIMEOUT = float(os.getenv("API_TEST_STREAM_TIMEOUT", "60"))

def _make_stream_request(text: str) -> dict:
    return {
        "jsonrpc": "2.0",
        "method": "message/stream",
        "id": "test-1",
        "params": {
            "message": {
                "messageId": "msg-test-001",
                "role": "user",
                "kind": "message",
                "parts": [{"kind": "text", "text": text}],
            }
        },
    }


def _parse_sse_line(line: str) -> dict | None:
    if not line.startswith("data:"):
        return None
    raw = line[len("data:"):].strip()
    if not raw:
        return None
    return json.loads(raw)


def _extract_event(envelope: dict) -> dict | None:
    result = envelope.get("result")
    if isinstance(result, dict):
        return result
    return None


class TestHelloResponse:
    """Test that the agent responds without errors to any message."""

    def test_stream_response_uses_sse_content_type(self, auth_headers):
        with httpx.Client(base_url=BASE_URL, timeout=_STREAM_TIMEOUT, headers=auth_headers) as client:
            with client.stream("POST", RPC_PATH, json=_make_stream_request("Hello")) as response:
                assert response.status_code == 200
                assert "text/event-stream" in response.headers.get("content-type", "")

    def test_hello_stream_completes_without_errors(self, auth_headers):
        artifact_texts: list[str] = []
        final_event: dict | None = None

        with httpx.Client(base_url=BASE_URL, timeout=_STREAM_TIMEOUT, headers=auth_headers) as client:
            with client.stream("POST", RPC_PATH, json=_make_stream_request("Hello")) as response:
                assert response.status_code == 200

                for raw_line in response.iter_lines():
                    envelope = _parse_sse_line(raw_line)
                    if envelope is None:
                        continue
                    event = _extract_event(envelope)
                    if event is None:
                        continue

                    kind = event.get("kind")
                    if kind == "status-update":
                        state = (event.get("status") or {}).get("state", "")
                        if event.get("final") is True and state == "completed":
                            final_event = event
                    elif kind == "artifact-update":
                        artifact = event.get("artifact") or {}
                        for part in artifact.get("parts") or []:
                            text = part.get("text", "")
                            if text.strip():
                                artifact_texts.append(text.strip())

        assert len(artifact_texts) >= 1, "Expected at least one artifact-update event"
        assert final_event is not None, "Stream ended without a final 'completed' status-update"
        full_response = " ".join(artifact_texts).lower()
        assert "error" not in full_response, f"Response contains 'error': {full_response!r}"
        assert "technical issue" not in full_response, f"Response contains 'technical issue': {full_response!r}"
