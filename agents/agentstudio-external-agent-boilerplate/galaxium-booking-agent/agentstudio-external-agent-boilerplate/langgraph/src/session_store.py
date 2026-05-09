from __future__ import annotations

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from agentstudio_sdk.hooks import emit_hook  # type: ignore[import-untyped]

from .state import ConversationMessage


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass
class _ConversationSession:
    messages: list[ConversationMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=_utc_now)
    last_seen: datetime = field(default_factory=_utc_now)


@dataclass(frozen=True)
class ConversationTurn:
    messages: list[ConversationMessage]
    is_new: bool


class InMemorySessionStore:
    def __init__(
        self,
        *,
        ttl_seconds: float = 30 * 60,
        max_messages: int = 20,
    ) -> None:
        self.ttl = timedelta(seconds=max(0.001, ttl_seconds))
        self.max_messages = max(1, max_messages)
        self._sessions: dict[str, _ConversationSession] = {}
        self._locks: defaultdict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

    @asynccontextmanager
    async def turn(self, context_id: str, user_text: str) -> AsyncIterator[ConversationTurn]:
        async with self._locks[context_id]:
            yield await self._begin_turn(context_id, user_text)

    def append_assistant_message(self, context_id: str, content: str) -> None:
        session = self._sessions.get(context_id)
        if session is None:
            return

        session.messages.append({"role": "assistant", "content": content})
        session.last_seen = _utc_now()
        self._trim_messages(session)

    async def end_session(self, context_id: str, reason: str = "ended") -> None:
        async with self._locks[context_id]:
            session = self._sessions.pop(context_id, None)
            self._locks.pop(context_id, None)

        if session is not None:
            await self._emit_session_end(context_id, session, reason)

    async def expire_stale_sessions(self) -> int:
        now = _utc_now()
        expired = [
            (context_id, session)
            for context_id, session in self._sessions.items()
            if self._is_expired(session, now) and not self._locks[context_id].locked()
        ]

        for context_id, _ in expired:
            self._sessions.pop(context_id, None)
            self._locks.pop(context_id, None)

        for context_id, session in expired:
            await self._emit_session_end(context_id, session, "idle_timeout")

        return len(expired)

    async def close(self, reason: str = "shutdown") -> None:
        sessions = list(self._sessions.items())
        self._sessions.clear()
        self._locks.clear()

        for context_id, session in sessions:
            await self._emit_session_end(context_id, session, reason)

    async def _begin_turn(self, context_id: str, user_text: str) -> ConversationTurn:
        now = _utc_now()
        session = self._sessions.get(context_id)
        if session is not None and self._is_expired(session, now):
            self._sessions.pop(context_id, None)
            await self._emit_session_end(context_id, session, "idle_timeout")
            session = None

        is_new = session is None
        if session is None:
            session = _ConversationSession(created_at=now, last_seen=now)
            self._sessions[context_id] = session

        session.messages.append({"role": "user", "content": user_text})
        session.last_seen = now
        self._trim_messages(session)

        return ConversationTurn(
            messages=[message.copy() for message in session.messages],
            is_new=is_new,
        )

    def _is_expired(self, session: _ConversationSession, now: datetime) -> bool:
        return now - session.last_seen >= self.ttl

    def _trim_messages(self, session: _ConversationSession) -> None:
        if len(session.messages) > self.max_messages:
            session.messages = session.messages[-self.max_messages :]

    async def _emit_session_end(
        self,
        context_id: str,
        session: _ConversationSession,
        reason: str,
    ) -> None:
        await emit_hook(
            "session_end",
            {
                "context_id": context_id,
                "reason": reason,
                "message_count": len(session.messages),
                "created_at": session.created_at.isoformat(),
                "last_seen": session.last_seen.isoformat(),
            },
        )
