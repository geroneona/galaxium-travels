from __future__ import annotations

# Disable specific pylint checks that are noisy for optional/plug-in client probing
# pylint: disable=abstract-class-instantiated,not-callable
import asyncio
from typing import Any

from a2a.client import Client  # type: ignore[import-untyped]

from .logger import get_logger


class A2AClientAdapter:
    """Defensive adapter that probes several possible A2A package/module names.

    The upstream repository's package metadata is `a2a-sdk`, but its top-level
    import name may be `a2a` or `a2a_sdk`. This adapter tries multiple module
    names and common client entry points so installing from the GitHub repo
    will be usable without hard-coding a single import.
    """

    def __init__(self) -> None:
        self._client: Any | None = None
        self._logger = get_logger(__name__)

        # Construct the client directly using the `Client` class imported
        # above. Let any constructor exceptions be logged so behavior
        # mirrors the example's direct imports.
        try:
            # Client may be typed as abstract by stubs; ignore abstract check
            self._client = Client()  # type: ignore[abstract]
            self._logger.info("A2A client initialized via a2a.client.Client")
        except Exception:
            self._logger.debug("Failed to initialize a2a.client.Client")

        if self._client is None:
            self._logger.debug("No A2A client module found during probe")

    async def send_message(self, from_agent: str, to_agent: str, message: str) -> str:
        """Send a message via the underlying A2A client and return any reply.

        Raises RuntimeError when the A2A client is not available or doesn't
        expose a usable send/publish primitive.
        """
        if self._client is None:
            self._logger.debug("Attempted to send A2A message but no client available")
            raise RuntimeError("a2a client not available; install dependencies")

        # Try a variety of common method names and parameter mappings. Be
        # defensive: SDKs vary in naming and parameter shapes.
        method_names = (
            "send",
            "publish",
            "send_message",
            "emit",
            "publish_event",
            "send_event",
            "publish_message",
            "send_async",
        )

        # Common parameter mappings to attempt (kwargs). The adapter will
        # try each mapping in-order and fall back to positional call.
        param_variants = [
            {
                "from_agent": from_agent,
                "to_agent": to_agent,
                "message": message,
            },
            {"from": from_agent, "to": to_agent, "body": message},
            {"sender": from_agent, "recipient": to_agent, "content": message},
            {"source": from_agent, "target": to_agent, "payload": message},
            {"from_agent": from_agent, "to_agent": to_agent, "text": message},
        ]

        async def _try_invoke(method) -> str | None:
            # Try kwarg variants
            for params in param_variants:
                try:
                    result = method(**params)
                except TypeError:
                    result = None
                except Exception as exc:  # pragma: no cover - runtime
                    self._logger.debug("A2A method %s raised: %s", method, exc)
                    result = None
                if result is None:
                    continue
                if asyncio.iscoroutine(result):
                    return await result
                return str(result)

            # Try positional fallback
            try:
                result = method(from_agent, to_agent, message)
            except TypeError:
                try:
                    result = method(
                        from_agent=from_agent,
                        to_agent=to_agent,
                        message=message,
                    )
                except Exception:
                    result = None
            except Exception as exc:  # pragma: no cover - runtime
                self._logger.debug("A2A method %s raised: %s", method, exc)
                result = None

            if result is None:
                return None
            if asyncio.iscoroutine(result):
                return await result
            return str(result)

        for method_name in method_names:
            method = getattr(self._client, method_name, None)
            if not callable(method):
                continue
            out = await _try_invoke(method)
            if out is not None:
                return out

        # Some clients may expose a top-level callable
        if callable(self._client):
            out = await _try_invoke(self._client)
            if out is not None:
                return out

            try:
                result = self._client(from_agent, to_agent, message)
            except Exception:
                result = None
            if result is None:
                self._logger.error("A2A client found but no usable send method detected")
                raise RuntimeError("a2a client found but no usable send method detected")
            if asyncio.iscoroutine(result):
                return await result
            return str(result)

        self._logger.error("A2A client found but no usable send method detected")
        raise RuntimeError("a2a client found but no usable send method detected")
