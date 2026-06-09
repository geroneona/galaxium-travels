import json
from typing import Any

from agentstudio_sdk.llm import LLM  # type: ignore[import-untyped]
from agentstudio_sdk.mcp_server_adapter import MCP_Server  # type: ignore[import-untyped]
from openinference.instrumentation import using_metadata
from langgraph.graph import StateGraph
from ..state import AgentState
from ..logger import get_logger
from .base import BaseAgent

logger = get_logger(__name__)


class BaseAgentWithMCP(BaseAgent):
    mcp = True

    def __init__(self, model: LLM, graph: StateGraph, mcp_server: MCP_Server):
        super().__init__(model, graph)

        self.mcp_server = mcp_server
        self.tools: list[dict] = []
        self.tool_info: list[dict] = []

    async def _run_init(self) -> None:
        await super()._run_init()
        await self.init_tools()

    async def init_tools(self) -> None:
        tools = await self.mcp_server.get_tools_schema()
        self.tools = list(tools or [])
        self.tool_info = [
            {
                "name": t["toolSpec"]["name"],
                "description": t["toolSpec"]["description"],
            }
            for t in self.tools
        ]

    async def generate(self, prompt: str | list[dict[str, Any]], tools: list | None = None) -> Any:
        use_discovered_tools = tools is None or tools is self.tools
        await self.init()
        effective_tools = self.tools if use_discovered_tools else tools
        with using_metadata({"agent_name": self.__class__.__name__}):
            return await self.model.generate(prompt, effective_tools)

    def get_tool_info(self) -> list[dict]:
        return self.tool_info

    async def call_mcp(self, payload) -> object:
        with using_metadata(
            {
                "agent_name": self.__class__.__name__,
                "tool_transport": "mcp",
            }
        ):
            return await self.mcp_server.call_mcp("tools/call", payload)

    def extract_tool_requests(self, resp_raw: Any) -> list[dict[str, Any]]:
        tool_requests: list[dict[str, Any]] = []

        if isinstance(resp_raw, dict):
            content = resp_raw.get("output", {}).get("message", {}).get("content", [])
            if isinstance(content, list):
                tool_requests.extend(
                    c["toolUse"]
                    for c in content
                    if isinstance(c, dict) and "toolUse" in c
                )
            if tool_requests:
                return tool_requests

            choices = resp_raw.get("choices") or []
            if choices and isinstance(choices[0], dict):
                message = choices[0].get("message", {})
                tool_calls = message.get("tool_calls", [])
                tool_requests.extend(self._tool_request_from_dict(call) for call in tool_calls)
            return [request for request in tool_requests if request.get("name")]

        choices = getattr(resp_raw, "choices", None)
        if choices and len(choices) > 0:
            message = getattr(choices[0], "message", None)
            tool_calls = getattr(message, "tool_calls", None) if message else None
            if tool_calls:
                tool_requests.extend(self._tool_request_from_object(call) for call in tool_calls)

        return [request for request in tool_requests if request.get("name")]

    def _tool_request_from_dict(self, tool_call: dict) -> dict[str, Any]:
        if not isinstance(tool_call, dict) or tool_call.get("type") != "function":
            return {}
        function = tool_call.get("function", {})
        return {
            "toolUseId": tool_call.get("id", ""),
            "name": function.get("name", ""),
            "input": self._decode_tool_arguments(function.get("arguments", "{}")),
        }

    def _tool_request_from_object(self, tool_call: Any) -> dict[str, Any]:
        if getattr(tool_call, "type", None) != "function":
            return {}
        function = getattr(tool_call, "function", None)
        return {
            "toolUseId": getattr(tool_call, "id", ""),
            "name": getattr(function, "name", ""),
            "input": self._decode_tool_arguments(getattr(function, "arguments", "{}")),
        }

    def _decode_tool_arguments(self, arguments: Any) -> dict[str, Any]:
        if isinstance(arguments, dict):
            return arguments
        if isinstance(arguments, str) and arguments:
            try:
                decoded = json.loads(arguments)
                return decoded if isinstance(decoded, dict) else {}
            except json.JSONDecodeError:
                logger.warning("Failed to decode tool arguments as JSON: %s", arguments)
        return {}

    async def handle_message(self, state: AgentState) -> AgentState:
        raise NotImplementedError()
