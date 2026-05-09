from __future__ import annotations

from agentstudio_sdk.hooks import HOOK_EVENTS, HookRegistry
from src.logger import get_logger

logger = get_logger(__name__)


def _build_handler(event_name: str):
    def _handler(payload: dict) -> None:
        logger.info(
            "hook=%s context_id=%s task_id=%s agent=%s tool=%s input=%s output=%s error=%s",
            event_name,
            payload.get("context_id"),
            payload.get("task_id"),
            payload.get("agent_name"),
            payload.get("tool_name"),
            payload.get("input"),
            payload.get("output") or payload.get("tool_output"),
            payload.get("error"),
        )

    return _handler


def register_agentstudio_hooks(registry: HookRegistry) -> None:
    for event_name in HOOK_EVENTS:
        registry.register(event_name, _build_handler(event_name))
