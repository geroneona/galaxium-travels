import asyncio
import importlib.util
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

SDK_ROOT = PROJECT_ROOT.parent / "agentstudio-sdk" / "src" / "agentstudio_sdk"
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

from agentstudio_sdk.hooks import clear_hooks, register_hook, use_hook_context  # noqa: E402
from src.demo_tools import (  # noqa: E402
    parse_demo_tool_request,
    run_demo_tool_with_hooks,
)


@pytest.fixture(autouse=True)
def _reset_hooks():
    clear_hooks()
    yield
    clear_hooks()


def test_parse_demo_tool_request_supports_known_commands():
    assert parse_demo_tool_request("/demo-tool context-summary") == {
        "tool_name": "context-summary",
        "tool_input": {},
    }
    assert parse_demo_tool_request("/demo-tool error custom failure") == {
        "tool_name": "error",
        "tool_input": {"message": "custom failure"},
    }


def test_run_demo_tool_with_hooks_emits_tool_call_and_result():
    events = []
    register_hook("tool_call", lambda payload: events.append(("call", payload.copy())))
    register_hook("tool_result", lambda payload: events.append(("result", payload.copy())))

    request = {"tool_name": "context-summary", "tool_input": {}}
    with use_hook_context(context_id="ctx-1"):
        output = asyncio.run(run_demo_tool_with_hooks(request, "hello world"))

    assert "words: 2" in output
    assert events[0][0] == "call"
    assert events[1][0] == "result"


def test_run_demo_tool_with_hooks_emits_tool_error():
    events = []
    register_hook("tool_error", lambda payload: events.append(payload.copy()))

    request = {"tool_name": "error", "tool_input": {"message": "boom"}}
    output = asyncio.run(run_demo_tool_with_hooks(request, "hello world"))

    assert output == "RLM demo tool 'error' failed: boom"
    assert events[0]["event"] == "tool_error"
    assert events[0]["error"] == "boom"
