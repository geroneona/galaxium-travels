import asyncio
import importlib
import importlib.util
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SDK_ROOT = PROJECT_ROOT / "src" / "agentstudio_sdk"
sdk_package = types.ModuleType("agentstudio_sdk")
sdk_package.__path__ = [str(SDK_ROOT)]
sys.modules.setdefault("agentstudio_sdk", sdk_package)


def _load_sdk_submodule(name: str):
    module_name = f"agentstudio_sdk.{name}"
    if module_name in sys.modules:
        return sys.modules[module_name]

    spec = importlib.util.spec_from_file_location(
        module_name,
        SDK_ROOT / f"{name}.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


_load_sdk_submodule("logger")
_load_sdk_submodule("hooks")
_load_sdk_submodule("mcp_server_adapter")

from agentstudio_sdk.hooks import (  # noqa: E402
    clear_hooks,
    emit_hook,
    emit_hook_sync,
    load_hooks_from_env,
    register_hook,
    use_hook_context,
)
from agentstudio_sdk.mcp_server_adapter import MCP_Server  # noqa: E402


@pytest.fixture(autouse=True)
def _reset_hooks():
    clear_hooks()
    yield
    clear_hooks()


def test_emit_hook_merges_context_and_ignores_handler_failures():
    captured = []

    def _broken(_payload):
        raise RuntimeError("boom")

    def _capture(payload):
        captured.append(payload.copy())

    register_hook("output", _broken)
    register_hook("output", _capture)

    with use_hook_context(context_id="ctx-1", task_id="task-1"):
        payload = asyncio.run(emit_hook("output", {"output": "hello"}))

    assert payload["event"] == "output"
    assert payload["context_id"] == "ctx-1"
    assert payload["task_id"] == "task-1"
    assert payload["output"] == "hello"
    assert captured == [payload]


def test_session_end_hook_is_supported():
    captured = []
    register_hook("session_end", lambda payload: captured.append(payload.copy()))

    payload = asyncio.run(
        emit_hook(
            "session_end",
            {
                "context_id": "ctx-1",
                "reason": "idle_timeout",
            },
        )
    )

    assert payload["event"] == "session_end"
    assert captured == [payload]


def test_emit_hook_isolates_payload_between_handlers():
    captured = []

    def _mutate(payload):
        payload["output"] = "mutated"
        payload["details"]["status"] = "mutated"

    def _capture(payload):
        captured.append(payload.copy())

    register_hook("output", _mutate)
    register_hook("output", _capture)

    payload = asyncio.run(
        emit_hook(
            "output",
            {
                "output": "hello",
                "details": {"status": "original"},
            },
        )
    )

    assert payload["output"] == "hello"
    assert payload["details"] == {"status": "original"}
    assert captured == [
        {
            "event": "output",
            "output": "hello",
            "details": {"status": "original"},
        }
    ]


def test_emit_hook_sync_schedules_async_handlers_on_running_loop():
    captured = []
    
    async def _exercise():
        completed = asyncio.Event()

        async def _capture(payload):
            captured.append(payload.copy())
            completed.set()

        register_hook("input", _capture)

        payload = emit_hook_sync("input", {"input": "hello"})

        await asyncio.wait_for(completed.wait(), timeout=1)
        return payload

    payload = asyncio.run(_exercise())

    assert captured == [payload]


def test_load_hooks_from_env_registers_module_hooks(tmp_path, monkeypatch):
    module_path = tmp_path / "temp_hook_module.py"
    module_path.write_text(
        "\n".join(
            [
                "EVENTS = []",
                "def _handler(payload):",
                "    EVENTS.append(payload.copy())",
                "def register_agentstudio_hooks(registry):",
                "    registry.register('input', _handler)",
            ]
        ),
        encoding="utf-8",
    )

    sys.path.insert(0, str(tmp_path))
    monkeypatch.setenv("AGENTSTUDIO_HOOKS", "temp_hook_module")
    try:
        assert load_hooks_from_env() == ["temp_hook_module"]
        asyncio.run(emit_hook("input", {"input": "hello"}))
        module = importlib.import_module("temp_hook_module")
        assert module.EVENTS[0]["input"] == "hello"
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop("temp_hook_module", None)


class _FakeSSEMCPServer(MCP_Server):
    def __init__(self, result):
        super().__init__(
            {
                "mcp_server_url": "http://example.com/sse",
                "auth_key": "",
            }
        )
        self._result = result

    async def call_mcp_sse(self, method, params=None):
        assert method == "tools/call"
        return self._result


def test_mcp_server_emits_tool_call_and_result_hooks():
    events = []
    register_hook("tool_call", lambda payload: events.append(("call", payload.copy())))
    register_hook("tool_result", lambda payload: events.append(("result", payload.copy())))

    server = _FakeSSEMCPServer({"content": [{"text": "ok"}]})

    with use_hook_context(context_id="ctx-1", agent_name="WeatherAgent"):
        result = asyncio.run(
            server.call_mcp(
                "tools/call",
                {"name": "lookup", "arguments": {"q": "x"}},
            )
        )

    assert result == {"content": [{"text": "ok"}]}
    assert events == [
        (
            "call",
            {
                "context_id": "ctx-1",
                "agent_name": "WeatherAgent",
                "event": "tool_call",
                "tool_name": "lookup",
                "tool_input": {"q": "x"},
                "tool_transport": "sse",
                "mcp_server_url": "http://example.com/sse",
            },
        ),
        (
            "result",
            {
                "context_id": "ctx-1",
                "agent_name": "WeatherAgent",
                "event": "tool_result",
                "tool_name": "lookup",
                "tool_input": {"q": "x"},
                "tool_transport": "sse",
                "mcp_server_url": "http://example.com/sse",
                "tool_output": "ok",
            },
        ),
    ]


def test_mcp_server_emits_tool_error_hook_for_empty_results():
    events = []
    register_hook("tool_call", lambda payload: events.append(("call", payload.copy())))
    register_hook("tool_error", lambda payload: events.append(("error", payload.copy())))

    server = _FakeSSEMCPServer({})

    asyncio.run(
        server.call_mcp(
            "tools/call",
            {"name": "lookup", "arguments": {"q": "x"}},
        )
    )

    assert events[0][0] == "call"
    assert events[1][0] == "error"
    assert events[1][1]["error"] == "Tool returned an empty or invalid response."


def test_mcp_server_preserves_sse_transport_errors_in_tool_error_hook(monkeypatch):
    events = []
    register_hook("tool_error", lambda payload: events.append(payload.copy()))

    server = MCP_Server(
        {
            "mcp_server_url": "http://example.com/sse",
            "auth_key": "",
        }
    )

    @asynccontextmanager
    async def _broken_sse_client(*args, **kwargs):
        raise RuntimeError("network down")
        yield

    monkeypatch.setattr(
        sys.modules["agentstudio_sdk.mcp_server_adapter"],
        "sse_client",
        _broken_sse_client,
    )

    result = asyncio.run(
        server.call_mcp(
            "tools/call",
            {"name": "lookup", "arguments": {"q": "x"}},
        )
    )

    assert result == {
        "isError": True,
        "error": {
            "message": "network down",
            "type": "RuntimeError",
        },
    }
    assert events == [
        {
            "event": "tool_error",
            "tool_name": "lookup",
            "tool_input": {"q": "x"},
            "tool_transport": "sse",
            "mcp_server_url": "http://example.com/sse",
            "error": "network down",
            "error_type": "RuntimeError",
        }
    ]
