import asyncio
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT.parents[1] / "agentstudio-sdk" / "src"))

from agentstudio_sdk.hooks import clear_hooks, register_hook, use_hook_context  # noqa: E402
from src.deepagent_activity_logger import log_node_activity  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_hooks():
    clear_hooks()
    yield
    clear_hooks()


class AIMessage:
    def __init__(self, content, tool_calls):
        self.content = content
        self.tool_calls = tool_calls


class ToolMessage:
    def __init__(self, name, content, status=None):
        self.name = name
        self.content = content
        self.status = status


def test_log_node_activity_emits_tool_call_and_result_hooks():
    events = []

    async def _capture_call(payload):
        events.append(("call", payload.copy()))

    async def _capture_result(payload):
        events.append(("result", payload.copy()))

    register_hook("tool_call", _capture_call)
    register_hook("tool_result", _capture_result)

    node_output = {
        "messages": [
            AIMessage("thinking", [{"name": "lookup", "args": {"q": "x"}}]),
            ToolMessage("lookup", "done"),
        ]
    }

    with use_hook_context(context_id="ctx-1"):
        asyncio.run(log_node_activity("planner", node_output))

    assert events == [
        (
            "call",
            {
                "context_id": "ctx-1",
                "event": "tool_call",
                "agent_name": "planner",
                "tool_name": "lookup",
                "tool_input": {"q": "x"},
            },
        ),
        (
            "result",
            {
                "context_id": "ctx-1",
                "event": "tool_result",
                "agent_name": "planner",
                "tool_name": "lookup",
                "tool_output": "done",
            },
        ),
    ]


def test_log_node_activity_emits_tool_error_hook():
    events = []
    register_hook("tool_error", lambda payload: events.append(payload.copy()))

    node_output = {"messages": [ToolMessage("lookup", "Error: failed to execute", status="error")]}

    asyncio.run(log_node_activity("planner", node_output))

    assert events[0]["event"] == "tool_error"
    assert events[0]["tool_name"] == "lookup"
    assert events[0]["error"] == "Error: failed to execute"
