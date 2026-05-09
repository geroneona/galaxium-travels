"""
SSE streaming happy-path test for the A2A agent.

Sends a ``message/stream`` JSON-RPC request and verifies that:
1. The server responds with ``text/event-stream`` content type.
2. At least one intermediate ``status-update`` event with state ``working``
   is received (carrying a reasoning/sub-agent step).
3. A ``artifact-update`` event carrying the final text is received.
4. A final ``status-update`` event with state ``completed`` arrives with
   ``final: true``, marking the end of the stream.
"""

import json
import os

import httpx
import pytest

# Allow override via environment variable; default matches the dev server.
BASE_URL = os.getenv("API_TEST_BASE_URL", "http://localhost:8000")

# The JSONRPC endpoint path (matches RPC_PATH env / default in settings.py).
RPC_PATH = os.getenv("RPC_PATH", "/v1/rpc")

ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

_AUTH_HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"} if ACCESS_TOKEN else {}

# Keep an ample timeout – the real deep-agent chain calls multiple sub-agents.
_STREAM_TIMEOUT = float(os.getenv("API_TEST_STREAM_TIMEOUT", "180"))

_STREAM_REQUEST = {
    "jsonrpc": "2.0",
    "method": "message/stream",
    "id": "sse-happy-path-1",
    "params": {
        "message": {
            "messageId": "msg-sse-test-001",
            "role": "user",
            "kind": "message",
            "parts": [
                {
                    "kind": "text",
                    "text": (
                        "Evaluate this candidate for a junior Python developer role.\n\n"
                        "## CV\nName: Alice Smith\n"
                        "Experience: 1 year Python scripting (data pipelines).\n"
                        "Education: BSc Computer Science.\n\n"
                        "## Job Description\nJunior Python Developer at Acme Corp.\n"
                        "Required: Python, REST APIs. Nice to have: AWS, FastAPI."
                    ),
                }
            ],
        }
    },
}


def _parse_sse_line(line: str) -> dict | None:
    """Return parsed JSON from a ``data:`` SSE line, or None for other lines."""
    if not line.startswith("data:"):
        return None
    raw = line[len("data:"):].strip()
    if not raw:
        return None
    return json.loads(raw)


def _extract_event(envelope: dict) -> dict | None:
    """
    A2A SSE envelopes are JSON-RPC success responses.

    The ``result`` field contains the actual A2A event object
    (Task, TaskStatusUpdateEvent, TaskArtifactUpdateEvent, …).
    """
    result = envelope.get("result")
    if isinstance(result, dict):
        return result
    return None


class TestSSEStreamingHappyPath:
    """Happy-path SSE streaming tests."""

    def test_stream_response_uses_sse_content_type(self):
        """The /v1/rpc streaming endpoint must respond with text/event-stream."""
        with httpx.Client(base_url=BASE_URL, timeout=_STREAM_TIMEOUT, headers=_AUTH_HEADERS) as client:
            with client.stream("POST", RPC_PATH, json=_STREAM_REQUEST) as response:
                assert response.status_code == 200, (
                    f"Expected 200, got {response.status_code}: {response.text}"
                )
                content_type = response.headers.get("content-type", "")
                assert "text/event-stream" in content_type, (
                    f"Expected text/event-stream, got: {content_type}"
                )

    def test_stream_delivers_working_then_completed(self):
        """
        Happy path: the stream must emit at least one ``working`` status-update
        (reasoning step) followed by an ``artifact-update`` with non-empty text
        and a final ``completed`` status-update.
        """
        working_states: list[dict] = []
        artifact_texts: list[str] = []
        final_event: dict | None = None

        with httpx.Client(base_url=BASE_URL, timeout=_STREAM_TIMEOUT, headers=_AUTH_HEADERS) as client:
            with client.stream("POST", RPC_PATH, json=_STREAM_REQUEST) as response:
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
                        if state == "working":
                            working_states.append(event)
                        if event.get("final") is True and state == "completed":
                            final_event = event

                    elif kind == "artifact-update":
                        artifact = event.get("artifact") or {}
                        for part in artifact.get("parts") or []:
                            text = part.get("text", "")
                            if text.strip():
                                artifact_texts.append(text.strip())

        # ── Assertions ──────────────────────────────────────────────────────

        assert len(working_states) >= 1, (
            "Expected at least one 'working' status-update event "
            "(reasoning / sub-agent step) but received none.\n"
            f"Artifact texts captured: {artifact_texts}"
        )

        assert len(artifact_texts) >= 1, (
            "Expected at least one artifact-update event with non-empty text "
            "(the final evaluation report) but received none."
        )

        assert final_event is not None, (
            "Stream ended without a final 'completed' status-update event."
        )

        # Sanity check: the final report must have meaningful content.
        final_report = artifact_texts[-1]
        assert len(final_report) > 50, (
            f"Final report looks too short ({len(final_report)} chars): "
            f"{final_report!r}"
        )
