import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(REPO_ROOT / "agentstudio-sdk" / "src"))

from agentstudio_sdk.hooks import clear_hooks, register_hook  # noqa: E402
from src.session_store import InMemorySessionStore  # noqa: E402


def test_session_store_records_history_and_session_end_on_expiry():
    async def run_test():
        events = []
        clear_hooks()
        register_hook("session_end", lambda payload: events.append(payload.copy()))
        store = InMemorySessionStore(ttl_seconds=0.01, max_messages=10)

        async with store.turn("ctx-1", "hello") as turn:
            assert turn.is_new is True
            assert turn.messages == [{"role": "user", "content": "hello"}]
            store.append_assistant_message("ctx-1", "hi")

        await asyncio.sleep(0.02)
        async with store.turn("ctx-1", "again") as next_turn:
            assert next_turn.is_new is True
            assert next_turn.messages == [{"role": "user", "content": "again"}]

        assert len(events) == 1
        assert events[0]["event"] == "session_end"
        assert events[0]["context_id"] == "ctx-1"
        assert events[0]["reason"] == "idle_timeout"
        assert events[0]["message_count"] == 2

        await store.close()
        clear_hooks()

    asyncio.run(run_test())


def test_session_store_trims_to_recent_messages():
    async def run_test():
        clear_hooks()
        store = InMemorySessionStore(ttl_seconds=60, max_messages=3)

        async with store.turn("ctx-1", "one"):
            store.append_assistant_message("ctx-1", "two")

        async with store.turn("ctx-1", "three"):
            store.append_assistant_message("ctx-1", "four")

        async with store.turn("ctx-1", "five") as turn:
            assert turn.messages == [
                {"role": "user", "content": "three"},
                {"role": "assistant", "content": "four"},
                {"role": "user", "content": "five"},
            ]

        await store.close()
        clear_hooks()

    asyncio.run(run_test())
