import asyncio
import copy
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(REPO_ROOT / "agentstudio-sdk" / "src"))

from agentstudio_sdk.hooks import clear_hooks, register_hook  # noqa: E402
from src.agentic_agent_executor import AgenticAgentExecutor  # noqa: E402
from src.session_store import InMemorySessionStore  # noqa: E402


class FakeWorkflow:
    def __init__(self):
        self.states = []

    async def ainvoke(self, state):
        self.states.append(copy.deepcopy(state))
        return {"response": f"reply-{len(self.states)}"}


class FakeContext:
    def __init__(self, text: str, context_id: str = "ctx-1", task_id: str = "task-1"):
        self.context_id = context_id
        self.task_id = task_id
        self.message = None
        self._text = text

    def get_user_input(self):
        return self._text


class FakeEventQueue:
    def __init__(self):
        self.events = []

    async def enqueue_event(self, event):
        self.events.append(event)


def test_executor_passes_conversation_history_by_context_id():
    async def run_test():
        clear_hooks()
        session_starts = []
        register_hook("session_start", lambda payload: session_starts.append(payload.copy()))

        workflow = FakeWorkflow()
        store = InMemorySessionStore(ttl_seconds=60, max_messages=10)
        executor = AgenticAgentExecutor(workflow, store)
        queue = FakeEventQueue()

        await executor.execute(FakeContext("hello"), queue)
        await executor.execute(FakeContext("what did I say?"), queue)

        assert workflow.states[0]["messages"] == [
            {"role": "user", "content": "hello"},
        ]
        assert workflow.states[1]["messages"] == [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "reply-1"},
            {"role": "user", "content": "what did I say?"},
        ]
        assert [payload["context_id"] for payload in session_starts] == ["ctx-1"]
        assert len(queue.events) == 2

        await store.close()
        clear_hooks()

    asyncio.run(run_test())


def test_executor_keeps_sessions_isolated():
    async def run_test():
        clear_hooks()
        workflow = FakeWorkflow()
        store = InMemorySessionStore(ttl_seconds=60, max_messages=10)
        executor = AgenticAgentExecutor(workflow, store)
        queue = FakeEventQueue()

        await executor.execute(FakeContext("hello", context_id="ctx-1"), queue)
        await executor.execute(FakeContext("hello", context_id="ctx-2"), queue)

        assert workflow.states[0]["messages"] == [{"role": "user", "content": "hello"}]
        assert workflow.states[1]["messages"] == [{"role": "user", "content": "hello"}]

        await store.close()
        clear_hooks()

    asyncio.run(run_test())
