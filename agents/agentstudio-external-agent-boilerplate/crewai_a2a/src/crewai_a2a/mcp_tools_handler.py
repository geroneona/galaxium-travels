"""
MCP Tools Handler

Converts MCP tools from an HTTP-based MCP server into CrewAI BaseTool objects.
Uses the official `mcp` library (streamable HTTP transport) for server communication.
"""

import asyncio
import concurrent.futures
import logging
from collections.abc import Coroutine
from typing import Any, Optional, TypeVar
from urllib.parse import urlparse

_T = TypeVar("_T")

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from mcp.types import Tool

from crewai.tools import BaseTool
from crewai.tools.mcp_native_tool import MCPNativeTool
from crewai.mcp import MCPClient
from agentstudio_sdk.hooks import emit_hook
from pydantic import BaseModel as PydanticBaseModel, Field, create_model
from crewai.mcp.transports.http import HTTPTransport


logger = logging.getLogger(__name__)



async def _list_tools_async(server_url: str, headers: dict[str, str]) -> list[Tool]:
    """Connect to the MCP server and return a list of tool dicts with name and description."""
    async with streamablehttp_client(server_url, headers=headers) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            result = await session.list_tools()
            return result.tools

def _run_async_in_thread(coro: Coroutine[Any, Any, _T]) -> _T:
    """Run an async coroutine in a dedicated thread with its own event loop."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result(timeout=300)


def _extract_server_name(server_url: str) -> str:
    """Extract clean server name from URL for tool prefixing."""

    parsed = urlparse(server_url)
    domain = parsed.netloc.replace(".", "_")
    path = parsed.path.replace("/", "_").strip("_")
    return f"{domain}_{path}" if path else domain

def _json_schema_to_pydantic(tool_name: str, json_schema: dict[str, Any]) -> type:
    """Convert JSON Schema to Pydantic model for tool arguments.
    Args:
        tool_name: Name of the tool (used for model naming)
        json_schema: JSON Schema dict with 'properties', 'required', etc.
    Returns:
        Pydantic BaseModel class
    """
    from pydantic import Field, create_model

    properties = json_schema.get("properties", {})
    required_fields = json_schema.get("required", [])

    field_definitions: dict[str, Any] = {}

    for field_name, field_schema in properties.items():
        field_type = _json_type_to_python(field_schema)
        field_description = field_schema.get("description", "")

        is_required = field_name in required_fields

        if is_required:
            field_definitions[field_name] = (
                field_type,
                Field(..., description=field_description),
            )
        else:
            field_definitions[field_name] = (
                field_type | None,
                Field(default=None, description=field_description),
            )

    model_name = f"{tool_name.replace('-', '_').replace(' ', '_')}Schema"
    return create_model(model_name, **field_definitions)  # type: ignore[no-any-return]

def _json_type_to_python(field_schema: dict[str, Any]) -> type:
    """Convert JSON Schema type to Python type.
    Args:
        field_schema: JSON Schema field definition
    Returns:
        Python type
    """

    json_type = field_schema.get("type")

    if "anyOf" in field_schema:
        types: list[type] = []
        for option in field_schema["anyOf"]:
            if "const" in option:
                types.append(str)
            else:
                types.append(self._json_type_to_python(option))
        unique_types = list(set(types))
        if len(unique_types) > 1:
            result: Any = unique_types[0]
            for t in unique_types[1:]:
                result = result | t
            return result  # type: ignore[no-any-return]
        return unique_types[0]

    type_mapping: dict[str | None, type] = {
        "string": str,
        "number": float,
        "integer": int,
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    return type_mapping.get(json_type, Any)


class HookedMCPNativeTool(MCPNativeTool):
    """CrewAI MCP tool wrapper that emits AgentStudio runtime hooks."""

    def _hook_payload(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        return {
            "tool_name": self.original_tool_name,
            "tool_server": self.server_name,
            "tool_input": kwargs,
        }

    @staticmethod
    def _extract_content_text(content: Any) -> str | None:
        if not isinstance(content, list) or not content:
            return None

        first_item = content[0]
        if isinstance(first_item, dict) and first_item.get("text") is not None:
            return str(first_item["text"])
        if hasattr(first_item, "text"):
            return str(first_item.text)
        return str(first_item)

    @staticmethod
    def _result_field(result: Any, field: str) -> Any:
        if isinstance(result, dict):
            return result.get(field)
        return getattr(result, field, None)

    @classmethod
    def _is_tool_error_result(cls, result: Any) -> bool:
        if result is None:
            return True
        if cls._result_field(result, "isError"):
            return True
        return cls._result_field(result, "error") is not None

    @classmethod
    def _extract_tool_error(cls, result: Any) -> str:
        error = cls._result_field(result, "error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        if error:
            return str(error)

        content = cls._result_field(result, "content")
        text = cls._extract_content_text(content)
        if text:
            return text

        return "Tool returned an error response."

    @classmethod
    def _stringify_result(cls, result: Any) -> str:
        if isinstance(result, str):
            return result

        content = cls._result_field(result, "content")
        text = cls._extract_content_text(content)
        if text:
            return text
        if content:
            return str(content)

        error = cls._result_field(result, "error")
        if isinstance(error, dict):
            message = error.get("message")
            if message:
                return str(message)
        if error:
            return str(error)

        return str(result)

    async def _run_async(self, **kwargs) -> str:
        hook_payload = self._hook_payload(kwargs)
        await emit_hook("tool_call", hook_payload)

        if self._mcp_client.connected:
            await self._mcp_client.disconnect()

        await self._mcp_client.connect()

        try:
            try:
                result = await self._mcp_client.call_tool(
                    self.original_tool_name,
                    kwargs,
                )
            except Exception as exc:
                error_str = str(exc).lower()
                if (
                    "not connected" in error_str
                    or "connection" in error_str
                    or "send" in error_str
                ):
                    await self._mcp_client.disconnect()
                    await self._mcp_client.connect()
                    result = await self._mcp_client.call_tool(
                        self.original_tool_name,
                        kwargs,
                    )
                else:
                    raise
        except Exception as exc:
            await emit_hook(
                "tool_error",
                {
                    **hook_payload,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            raise
        finally:
            await self._mcp_client.disconnect()

        if self._is_tool_error_result(result):
            error = self._extract_tool_error(result)
            await emit_hook(
                "tool_error",
                {
                    **hook_payload,
                    "error": error,
                },
            )
            return error

        output = self._stringify_result(result)
        await emit_hook(
            "tool_result",
            {
                **hook_payload,
                "tool_output": output,
            },
        )
        return output

def get_mcp_tools(
    server_url: str,
    auth_headers: dict[str, str] | None = None,
) -> list[BaseTool]:
    """
    Discover tools from an MCP server and return them as CrewAI BaseTool objects.
    Args:
        server_url: URL of the MCP server endpoint.
        auth_headers: Optional HTTP headers (e.g. {"Authorization": "Bearer …"}).
    Returns:
        List of CrewAI BaseTool objects ready to be passed to an Agent's `tools=` param.
    """
    headers = dict(auth_headers or {})

    try:
        tools = _run_async_in_thread(_list_tools_async(server_url, headers))
    except Exception as exc:
        logger.error("Failed to load tools from MCP server %s: %s", server_url, exc)
        return []

    server_name = _extract_server_name(server_url)
    mcp_client = MCPClient(
        transport = HTTPTransport(url=server_url, headers=headers, streamable=False),
        cache_tools_list = True
    )

    crewai_tools: list[BaseTool] = []
    for tool in tools:
        args_schema = _json_schema_to_pydantic(tool.name, tool.inputSchema)
        crewai_tools.append(HookedMCPNativeTool(
            mcp_client = mcp_client,
            server_name = server_name,
            tool_name = tool.name,
            tool_schema = {
                "description": tool.description,
                "args_schema": args_schema,
            },
        ))


    logger.info("Loaded %d tool(s) from MCP server %s", len(crewai_tools), server_url)
    return crewai_tools
