import sys
from pathlib import Path

from fastapi.testclient import TestClient

from a2a.types import Message, Role, TextPart

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src import main  # noqa: E402

client = TestClient(main.app)


def test_get_agent_card():
    resp = client.get("/.well-known/agent-card.json")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert "name" in data and "url" in data


class FakeAgentExecutor:
    async def execute(self, context, event_queue) -> None:
        await event_queue.enqueue_event(
            Message(
                context_id=context.context_id,
                message_id="reply-1",
                parts=[TextPart(text=f"Echo: {context.get_user_input()}")],
                role=Role.agent,
                task_id=context.task_id,
            )
        )

    async def cancel(self, context, event_queue) -> None:
        return None


def _message_payload() -> tuple[str, dict]:
    message = {
        "contextId": "CONTEXT_ID",
        "kind": "message",
        "messageId": "msg-1",
        "parts": [{"kind": "text", "text": "What's the weather in Prague"}],
        "role": "user",
    }

    if main.settings.A2A_PROTOCOL == "JSONRPC":
        return (
            main.settings.agent_endpoint_path,
            {
                "id": "test-request-1",
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {"message": message},
            },
        )

    return (
        "/v1/message:send",
        {
            "message": {
                "content": [{"text": "What's the weather in Prague"}],
                "contextId": "CONTEXT_ID",
                "messageId": "msg-1",
                "role": "ROLE_USER",
            }
        },
    )


def _reply_text(data: dict) -> str:
    result = data.get("result", data)
    message = result.get("message") or result.get("msg") or result
    parts = message.get("parts") or message.get("content") or []
    if not parts:
        return ""
    return str(parts[0].get("text") or "")


def test_weather_conversation(monkeypatch):
    monkeypatch.setattr(main._REQUEST_HANDLER, "agent_executor", FakeAgentExecutor())

    path, payload = _message_payload()
    resp = client.post(path, json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    assert _reply_text(data) == "Echo: What's the weather in Prague"
