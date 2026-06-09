import asyncio
import sys
from pathlib import Path

import pytest
from pydantic import create_model

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))
sys.path.insert(0, str(PROJECT_ROOT.parent / "agentstudio-sdk" / "src"))

from crewai_a2a.mcp_tools_handler import HookedMCPNativeTool  # noqa: E402
from agentstudio_sdk.hooks import clear_hooks, register_hook, use_hook_context  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_hooks():
    clear_hooks()
    yield
    clear_hooks()


class _FakeContent:
    def __init__(self, text: str):
        self.text = text


class _FakeResult:
    def __init__(self, text: str):
        self.content = [_FakeContent(text)]


class _FakeErrorResult:
    def __init__(self, message: str):
        self.isError = True
        self.error = {"message": message}
        self.content = [_FakeContent(message)]


class _FakeMCPClient:
    def __init__(self, result=None, exc: Exception | None = None):
        self.connected = False
        self._result = result
        self._exc = exc

    async def connect(self):
        self.connected = True

    async def disconnect(self):
        self.connected = False

    async def call_tool(self, name, kwargs):
        if self._exc is not None:
            raise self._exc
        return self._result


def _build_tool(fake_client):
    args_schema = create_model("LookupArgs", q=(str, ...))
    return HookedMCPNativeTool(
        mcp_client=fake_client,
        server_name="example_server",
        tool_name="lookup",
        tool_schema={
            "description": "Look up a value",
            "args_schema": args_schema,
        },
    )


def test_hooked_mcp_native_tool_emits_tool_call_and_result():
    events = []
    register_hook("tool_call", lambda payload: events.append(("call", payload.copy())))
    register_hook("tool_result", lambda payload: events.append(("result", payload.copy())))

    tool = _build_tool(_FakeMCPClient(result=_FakeResult("ok")))

    with use_hook_context(context_id="ctx-1", agent_name="Term Reader Agent"):
        output = asyncio.run(tool._run_async(q="x"))

    assert output == "ok"
    assert events == [
        (
            "call",
            {
                "context_id": "ctx-1",
                "agent_name": "Term Reader Agent",
                "event": "tool_call",
                "tool_name": "lookup",
                "tool_server": "example_server",
                "tool_input": {"q": "x"},
            },
        ),
        (
            "result",
            {
                "context_id": "ctx-1",
                "agent_name": "Term Reader Agent",
                "event": "tool_result",
                "tool_name": "lookup",
                "tool_server": "example_server",
                "tool_input": {"q": "x"},
                "tool_output": "ok",
            },
        ),
    ]


def test_hooked_mcp_native_tool_emits_tool_error():
    events = []
    register_hook("tool_error", lambda payload: events.append(payload.copy()))

    tool = _build_tool(_FakeMCPClient(exc=RuntimeError("boom")))

    with pytest.raises(RuntimeError):
        asyncio.run(tool._run_async(q="x"))

    assert events[0]["event"] == "tool_error"
    assert events[0]["error"] == "boom"


def test_hooked_mcp_native_tool_emits_tool_error_for_structured_mcp_failure():
    events = []
    register_hook("tool_call", lambda payload: events.append(("call", payload.copy())))
    register_hook("tool_error", lambda payload: events.append(("error", payload.copy())))
    register_hook("tool_result", lambda payload: events.append(("result", payload.copy())))

    tool = _build_tool(_FakeMCPClient(result=_FakeErrorResult("bad input")))

    output = asyncio.run(tool._run_async(q="x"))

    assert output == "bad input"
    assert events == [
        (
            "call",
            {
                "event": "tool_call",
                "tool_name": "lookup",
                "tool_server": "example_server",
                "tool_input": {"q": "x"},
            },
        ),
        (
            "error",
            {
                "event": "tool_error",
                "tool_name": "lookup",
                "tool_server": "example_server",
                "tool_input": {"q": "x"},
                "error": "bad input",
            },
        ),
    ]
