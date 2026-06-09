"""Runtime hook registry and helpers shared by all boilerplates."""

from __future__ import annotations

import asyncio
import copy
import importlib
import os
from collections.abc import Callable
from contextlib import contextmanager
from contextvars import ContextVar
from inspect import isawaitable
from typing import Any

from .logger import get_logger

logger = get_logger(__name__)

HOOK_EVENTS = (
    "session_start",
    "session_end",
    "input",
    "output",
    "error",
    "tool_call",
    "tool_result",
    "tool_error",
)
DEFAULT_HOOKS_ENV_VAR = "AGENTSTUDIO_HOOKS"

HookPayload = dict[str, Any]
HookHandler = Callable[[HookPayload], Any]

_CURRENT_HOOK_CONTEXT: ContextVar[HookPayload] = ContextVar(
    "agentstudio_hook_context",
    default={},
)


class HookRegistry:
    """In-memory registry for hook handlers."""

    def __init__(self) -> None:
        self._hooks = {event: [] for event in HOOK_EVENTS}
        self._loaded_modules: set[str] = set()

    def register(self, event: str, handler: HookHandler) -> None:
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        if handler not in self._hooks[event]:
            self._hooks[event].append(handler)

    def register_many(self, hooks: dict[str, Any]) -> None:
        for event, handlers in hooks.items():
            if isinstance(handlers, (list, tuple, set)):
                for handler in handlers:
                    self.register(event, handler)
            else:
                self.register(event, handlers)

    def handlers_for(self, event: str) -> list[HookHandler]:
        if event not in self._hooks:
            raise ValueError(f"Unknown hook event: {event}")
        return list(self._hooks[event])

    def has_loaded_module(self, module_name: str) -> bool:
        return module_name in self._loaded_modules

    def mark_module_loaded(self, module_name: str) -> None:
        self._loaded_modules.add(module_name)

    def clear(self) -> None:
        for handlers in self._hooks.values():
            handlers.clear()
        self._loaded_modules.clear()


HOOK_REGISTRY = HookRegistry()


def get_hook_context() -> HookPayload:
    """Return a shallow copy of the current request-scoped hook context."""
    return dict(_CURRENT_HOOK_CONTEXT.get())


@contextmanager
def use_hook_context(**updates: Any):
    """Temporarily extend the current hook context for nested calls."""
    current = get_hook_context()
    merged = {
        **current,
        **{key: value for key, value in updates.items() if value is not None},
    }
    token = _CURRENT_HOOK_CONTEXT.set(merged)
    try:
        yield merged
    finally:
        _CURRENT_HOOK_CONTEXT.reset(token)


def register_hook(event: str, handler: HookHandler) -> None:
    HOOK_REGISTRY.register(event, handler)


def register_hooks(hooks: dict[str, Any]) -> None:
    HOOK_REGISTRY.register_many(hooks)


def clear_hooks() -> None:
    HOOK_REGISTRY.clear()
    _CURRENT_HOOK_CONTEXT.set({})


def _build_payload(event: str, payload: HookPayload | None = None) -> HookPayload:
    merged = get_hook_context()
    merged["event"] = event
    if payload:
        merged.update(
            {key: value for key, value in payload.items() if value is not None}
        )
    return merged


def _handler_payload(payload: HookPayload) -> HookPayload:
    """Return an isolated payload copy for each handler invocation."""
    try:
        return copy.deepcopy(payload)
    except Exception:
        return dict(payload)


async def _run_handler_async(
    event: str,
    handler: HookHandler,
    payload: HookPayload,
) -> None:
    try:
        result = handler(_handler_payload(payload))
        if isawaitable(result):
            await result
    except Exception:
        logger.exception("Hook handler failed for event '%s'", event)


def _log_scheduled_handler_result(event: str, task: asyncio.Future) -> None:
    try:
        task.result()
    except Exception:
        logger.exception("Hook handler failed for event '%s'", event)


async def _await_handler_result(result: Any) -> None:
    await result


def _run_handler_sync(
    event: str,
    handler: HookHandler,
    payload: HookPayload,
) -> None:
    try:
        result = handler(_handler_payload(payload))
        if isawaitable(result):
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                asyncio.run(result)
            else:
                task = loop.create_task(_await_handler_result(result))
                task.add_done_callback(
                    lambda completed_task, *, hook_event=event: _log_scheduled_handler_result(
                        hook_event,
                        completed_task,
                    )
                )
    except Exception:
        logger.exception("Hook handler failed for event '%s'", event)


async def emit_hook(
    event: str,
    payload: HookPayload | None = None,
) -> HookPayload:
    merged = _build_payload(event, payload)
    for handler in HOOK_REGISTRY.handlers_for(event):
        await _run_handler_async(event, handler, merged)
    return merged


def emit_hook_sync(
    event: str,
    payload: HookPayload | None = None,
) -> HookPayload:
    merged = _build_payload(event, payload)
    for handler in HOOK_REGISTRY.handlers_for(event):
        _run_handler_sync(event, handler, merged)
    return merged


def load_hook_module(module_name: str) -> bool:
    """Import and register hooks from a module."""
    if HOOK_REGISTRY.has_loaded_module(module_name):
        return False

    module = importlib.import_module(module_name)
    registered = False

    register_fn = getattr(module, "register_agentstudio_hooks", None)
    if callable(register_fn):
        register_fn(HOOK_REGISTRY)
        registered = True

    hooks = getattr(module, "HOOKS", None)
    if isinstance(hooks, dict):
        register_hooks(hooks)
        registered = True

    if not registered:
        raise ValueError(
            f"Hook module '{module_name}' must expose "
            "'register_agentstudio_hooks' or 'HOOKS'"
        )

    HOOK_REGISTRY.mark_module_loaded(module_name)
    return True


def load_hooks_from_env(env_var: str = DEFAULT_HOOKS_ENV_VAR) -> list[str]:
    """Load hook modules listed in a comma-separated environment variable."""
    raw_value = os.getenv(env_var, "")
    module_names = [name.strip() for name in raw_value.split(",") if name.strip()]
    loaded_modules: list[str] = []

    for module_name in module_names:
        try:
            if load_hook_module(module_name):
                loaded_modules.append(module_name)
        except Exception:
            logger.exception("Failed to load hook module '%s'", module_name)

    return loaded_modules


__all__ = [
    "DEFAULT_HOOKS_ENV_VAR",
    "HOOK_EVENTS",
    "HOOK_REGISTRY",
    "HookRegistry",
    "clear_hooks",
    "emit_hook",
    "emit_hook_sync",
    "get_hook_context",
    "load_hook_module",
    "load_hooks_from_env",
    "register_hook",
    "register_hooks",
    "use_hook_context",
]
