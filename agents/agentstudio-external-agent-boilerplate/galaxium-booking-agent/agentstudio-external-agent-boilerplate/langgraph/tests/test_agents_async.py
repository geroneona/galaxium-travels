import asyncio
import sys
from pathlib import Path
from contextlib import contextmanager

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import src.agentic_agent_executor as executor_module  # noqa: E402
import src.agents.base as base_module  # noqa: E402
import src.agents.base_with_mcp as base_with_mcp_module  # noqa: E402
from src.agentic_agent_executor import AgenticAgentExecutor  # noqa: E402
from src.agents.base import BaseAgent  # noqa: E402
from src.agents.base_with_mcp import BaseAgentWithMCP  # noqa: E402


class FakeModel:
    def __init__(self, init_delay: float = 0):
        self.init_calls = 0
        self.generate_calls = []
        self.init_delay = init_delay

    async def init(self):
        self.init_calls += 1
        if self.init_delay:
            await asyncio.sleep(self.init_delay)

    async def generate(self, prompt, tools=None):
        self.generate_calls.append((prompt, tools))
        return {"content": prompt}


class FakeMCPServer:
    def __init__(self):
        self.get_tools_calls = 0
        self.call_mcp_calls = []

    async def get_tools_schema(self):
        self.get_tools_calls += 1
        return [
            {
                "toolSpec": {
                    "name": "lookup",
                    "description": "Look up a value",
                    "inputSchema": {"json": {"type": "object"}},
                }
            }
        ]

    async def call_mcp(self, method, payload):
        self.call_mcp_calls.append((method, payload))
        return {"content": [{"text": "ok"}]}


class RecordingContextManager:
    def __init__(self, sink, metadata):
        self._sink = sink
        self._metadata = metadata

    def __enter__(self):
        self._sink.append(self._metadata)
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


@contextmanager
def null_span_context_manager(*_args, **_kwargs):
    yield None


def test_base_agent_init_is_idempotent_and_generation_is_async():
    model = FakeModel()
    agent = BaseAgent(model, object())

    response = asyncio.run(agent.generate("hello"))
    asyncio.run(agent.init())

    assert model.init_calls == 1
    assert model.generate_calls == [("hello", None)]
    assert response == {"content": "hello"}


def test_mcp_agent_init_discovers_tools_and_calls_mcp_async():
    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    asyncio.run(agent.init())
    asyncio.run(agent.init())
    result = asyncio.run(agent.call_mcp({"name": "lookup", "arguments": {"q": "x"}}))

    assert model.init_calls == 1
    assert mcp_server.get_tools_calls == 1
    assert agent.tools[0]["toolSpec"]["name"] == "lookup"
    assert agent.get_tool_info() == [{"name": "lookup", "description": "Look up a value"}]
    assert mcp_server.call_mcp_calls == [
        ("tools/call", {"name": "lookup", "arguments": {"q": "x"}})
    ]
    assert result == {"content": [{"text": "ok"}]}


def test_mcp_agent_generate_initializes_tools_before_first_model_call():
    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    response = asyncio.run(agent.generate("hello"))

    assert model.init_calls == 1
    assert mcp_server.get_tools_calls == 1
    assert model.generate_calls == [
        (
            "hello",
            [
                {
                    "toolSpec": {
                        "name": "lookup",
                        "description": "Look up a value",
                        "inputSchema": {"json": {"type": "object"}},
                    }
                }
            ],
        )
    ]
    assert response == {"content": "hello"}


def test_mcp_agent_generate_supports_legacy_self_tools_argument_on_first_call():
    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    response = asyncio.run(agent.generate("hello", agent.tools))

    assert model.generate_calls == [
        (
            "hello",
            [
                {
                    "toolSpec": {
                        "name": "lookup",
                        "description": "Look up a value",
                        "inputSchema": {"json": {"type": "object"}},
                    }
                }
            ],
        )
    ]
    assert response == {"content": "hello"}


def test_mcp_agent_generate_allows_explicit_tool_disable_after_init():
    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    asyncio.run(agent.init())
    response = asyncio.run(agent.generate("hello", []))

    assert model.generate_calls == [("hello", [])]
    assert response == {"content": "hello"}


def test_base_agent_init_is_safe_under_concurrent_generate_calls():
    async def run_test():
        model = FakeModel(init_delay=0.01)
        agent = BaseAgent(model, object())
        await asyncio.gather(agent.generate("hello"), agent.generate("world"))
        assert model.init_calls == 1
        assert model.generate_calls == [("hello", None), ("world", None)]

    asyncio.run(run_test())


def test_base_agent_generate_sets_agent_metadata_context(monkeypatch):
    metadata_entries = []

    monkeypatch.setattr(
        base_module,
        "using_metadata",
        lambda metadata: RecordingContextManager(metadata_entries, metadata),
    )

    model = FakeModel()
    agent = BaseAgent(model, object())

    asyncio.run(agent.generate("hello"))

    assert metadata_entries == [{"agent_name": "BaseAgent"}]


def test_mcp_agent_call_mcp_sets_agent_metadata_context(monkeypatch):
    metadata_entries = []

    monkeypatch.setattr(
        base_with_mcp_module,
        "using_metadata",
        lambda metadata: RecordingContextManager(metadata_entries, metadata),
    )

    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    asyncio.run(agent.call_mcp({"name": "lookup", "arguments": {"q": "x"}}))

    assert metadata_entries == [
        {
            "agent_name": "BaseAgentWithMCP",
            "tool_transport": "mcp",
        }
    ]


def test_mcp_agent_generate_sets_agent_metadata_context(monkeypatch):
    metadata_entries = []

    monkeypatch.setattr(
        base_with_mcp_module,
        "using_metadata",
        lambda metadata: RecordingContextManager(metadata_entries, metadata),
    )

    model = FakeModel()
    mcp_server = FakeMCPServer()
    agent = BaseAgentWithMCP(model, object(), mcp_server)

    asyncio.run(agent.generate("hello"))

    assert metadata_entries == [{"agent_name": "BaseAgentWithMCP"}]


def test_agentic_executor_runs_workflow_when_tracing_is_disabled(monkeypatch):
    class FakeWorkflow:
        def __init__(self):
            self.calls = []

        async def ainvoke(self, state):
            self.calls.append(state)
            return {"response": "ok", "taskId": "task-1"}

    monkeypatch.setattr(
        executor_module,
        "create_agent_span",
        null_span_context_manager,
    )

    workflow = FakeWorkflow()
    executor = AgenticAgentExecutor(workflow)

    reply_text, context = asyncio.run(
        executor._invoke_workflow({"utterance": "hello"}, "ctx-1", "hello")
    )

    assert workflow.calls == [{"utterance": "hello"}]
    assert reply_text == "ok"
    assert context == {"response": "ok", "taskId": "task-1"}


def test_mcp_agent_extracts_tool_requests_from_supported_model_formats():
    agent = BaseAgentWithMCP(FakeModel(), object(), FakeMCPServer())

    bedrock_response = {
        "output": {
            "message": {
                "content": [
                    {
                        "toolUse": {
                            "toolUseId": "bedrock-1",
                            "name": "lookup",
                            "input": {"q": "x"},
                        }
                    }
                ]
            }
        }
    }
    azure_response = {
        "choices": [
            {
                "message": {
                    "tool_calls": [
                        {
                            "id": "azure-1",
                            "type": "function",
                            "function": {
                                "name": "lookup",
                                "arguments": "{\"q\":\"x\"}",
                            },
                        }
                    ]
                }
            }
        ]
    }

    assert agent.extract_tool_requests(bedrock_response) == [
        {"toolUseId": "bedrock-1", "name": "lookup", "input": {"q": "x"}}
    ]
    assert agent.extract_tool_requests(azure_response) == [
        {"toolUseId": "azure-1", "name": "lookup", "input": {"q": "x"}}
    ]
