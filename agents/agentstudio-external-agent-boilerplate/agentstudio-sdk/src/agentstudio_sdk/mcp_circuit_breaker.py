"""Circuit breaker for MCP tool calls.

Provides :class:`MCPServerWithCircuitBreaker`, a drop-in subclass of
:class:`~agentstudio_sdk.mcp_server_adapter.MCP_Server` that adds two levels
of automatic failure protection:

* **Tool-level**: after an unexpected exception from ``tools/call``, that tool
  is disabled for ``graceful_degradation_period`` seconds.  Calls during the window return
  an "unavailable" response without hitting the server.

* **Server-level**: a background timer calls ``get_tools_schema`` every
  ``graceful_degradation_period`` seconds.  If the probe raises or returns an
  empty list the server is disabled for ``graceful_degradation_period`` seconds;
  when the next probe succeeds the server is re-enabled.  Tool calls are blocked
  while the server is disabled.
"""

import asyncio
import time

from .mcp_server_adapter import MCP_Server
from .logger import get_logger

logger = get_logger(__name__)

DEFAULT_GRACEFUL_DEGRADATION_PERIOD: float = 60.0  # seconds


def _tool_unavailable_response(tool_name: str) -> dict:
    return {
        "content": [
            {
                "type": "text",
                "text": (
                    f"Tool '{tool_name}' is currently unavailable. "
                    "Please try again later."
                ),
            }
        ],
        "isError": True,
    }


class MCPServerWithCircuitBreaker(MCP_Server):
    """Subclass of :class:`MCP_Server` that adds circuit-breaking behaviour.

    Accepts the same ``credentials`` dict as :class:`MCP_Server` plus an
    optional ``graceful_degradation_period`` keyword argument.

    Parameters
    ----------
    credentials:
        Same dict accepted by :class:`MCP_Server` (must contain
        ``mcp_server_url`` and ``auth_key``).
    graceful_degradation_period:
        How many seconds a tool (or the whole server) stays disabled after a
        failure.  Defaults to 60 s.
    """

    def __init__(
        self,
        credentials: dict,
        graceful_degradation_period: float = DEFAULT_GRACEFUL_DEGRADATION_PERIOD,
    ) -> None:
        super().__init__(credentials)
        self._graceful_degradation_period = graceful_degradation_period

        # tool_name -> monotonic timestamp after which the tool is re-enabled
        self._disabled_tools: dict[str, float] = {}

        # Set when the server is disabled (monotonic). None means enabled.
        # Once the timestamp passes the server stays "logically" disabled until
        # the next successful get_tools_schema() health-check.
        self._server_disabled_until: float | None = None

        # Background asyncio task for periodic health checks (started on first get_tools_schema call)
        self._health_check_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_server_disabled(self) -> bool:
        return self._server_disabled_until is not None

    def _health_check_window_expired(self) -> bool:
        return (
            self._server_disabled_until is not None
            and time.monotonic() >= self._server_disabled_until
        )

    def _is_tool_disabled(self, tool_name: str) -> bool:
        until = self._disabled_tools.get(tool_name)
        if until is None:
            return False
        if time.monotonic() >= until:
            del self._disabled_tools[tool_name]
            logger.info("Circuit breaker: tool '%s' re-enabled after disable window.", tool_name)
            return False
        return True

    def _disable_tool(self, tool_name: str) -> None:
        self._disabled_tools[tool_name] = time.monotonic() + self._graceful_degradation_period
        logger.warning("Circuit breaker: tool '%s' disabled for %.0f s.", tool_name, self._graceful_degradation_period)

    def _disable_server(self) -> None:
        self._server_disabled_until = time.monotonic() + self._graceful_degradation_period
        logger.warning("Circuit breaker: MCP server '%s' disabled for %.0f s.", self.url, self._graceful_degradation_period)
    
    async def _run_health_check_loop(self) -> None:
        """Background task: probe the MCP server every graceful_degradation_period seconds."""
        while True:
            await asyncio.sleep(self._graceful_degradation_period)
            logger.info("Circuit breaker: running periodic health check for '%s'.", self.url)
            try:
                tools = await super().get_tools_schema()
                logger.info("Circuit breaker: health check for '%s' returned %d tools.", self.url, len(tools))
                if tools:
                    self._server_disabled_until = None
                else:
                    logger.warning("Circuit breaker: health check for '%s' returned empty tools list; disabling server.", self.url)
                    self._disable_server()
            except Exception as exc:
                logger.error("Circuit breaker: health check for '%s' failed: %s", self.url, exc, exc_info=True)
                self._disable_server()

    async def call_mcp(self, method: str, params: dict | None = None) -> object:
        """Call the MCP server with circuit-breaking for ``tools/call``."""
        if method != "tools/call":
            return await super().call_mcp(method, params)

        if self._health_check_task is None or self._health_check_task.done():
            self._health_check_task = asyncio.ensure_future(self._run_health_check_loop())
            logger.info("Circuit breaker: started periodic health check timer for '%s'.", self.url)

        tool_name = (params or {}).get("name", "<unknown>")

        if self._is_server_disabled():
            logger.info("Circuit breaker: server '%s' with tool '%s' is unavailable", self.url, tool_name)
            return _tool_unavailable_response(tool_name)

        if self._is_tool_disabled(tool_name):
            logger.info("Circuit breaker: tool '%s' is unavailable", tool_name)
            return _tool_unavailable_response(tool_name)

        try:
            return await super().call_mcp(method, params)
        except Exception as exc:
            logger.error("Circuit breaker: unexpected exception calling tool '%s': %s", tool_name, exc, exc_info=True)
            self._disable_tool(tool_name)
            return _tool_unavailable_response(tool_name)
