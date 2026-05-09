import asyncio
import json

import httpx
from mcp import ClientSession
from mcp.client.sse import sse_client

from .hooks import emit_hook
from .logger import get_logger
from .phoenix import create_tool_span, set_tool_output
logger = get_logger(__name__)


class MCP_Server:

    def __init__(self, credentials):
        self.url = credentials["mcp_server_url"]
        self.auth_key = credentials["auth_key"]
        self._is_sse = "/sse" in self.url.lower()

    def _tool_hook_payload(self, method, params=None) -> dict | None:
        if method != "tools/call" or not isinstance(params, dict):
            return None
        return {
            "tool_name": params.get("name"),
            "tool_input": params.get("arguments", {}),
            "tool_transport": "sse" if self._is_sse else "http",
            "mcp_server_url": self.url,
        }

    def _error_result(
        self,
        message: str,
        *,
        error_type: str | None = None,
    ) -> dict[str, object]:
        error: dict[str, object] = {"message": message}
        if error_type:
            error["type"] = error_type
        return {
            "isError": True,
            "error": error,
        }

    def _is_tool_error_result(self, result: object) -> bool:
        if result in (None, {}, []):
            return True
        if isinstance(result, dict):
            if result.get("isError"):
                return True
            if result.get("error") is not None:
                return True
        return False

    def _extract_tool_error(self, result: object) -> str:
        if isinstance(result, dict):
            error = result.get("error")
            if isinstance(error, dict):
                message = error.get("message")
                if message:
                    return str(message)
            if error:
                return str(error)
            if result.get("isError"):
                content = result.get("content")
                if isinstance(content, list) and content:
                    first_item = content[0]
                    if isinstance(first_item, dict) and first_item.get("text"):
                        return str(first_item["text"])
        return "Tool returned an empty or invalid response."

    def _extract_tool_error_type(self, result: object) -> str | None:
        if not isinstance(result, dict):
            return None
        error = result.get("error")
        if isinstance(error, dict):
            error_type = error.get("type")
            if error_type is not None:
                return str(error_type)
        return None

    def _summarise_tool_output(self, result: object) -> str:
        if isinstance(result, dict):
            content = result.get("content")
            if isinstance(content, list):
                text_parts = []
                for item in content:
                    if isinstance(item, dict) and item.get("text") is not None:
                        text_parts.append(str(item["text"]))
                if text_parts:
                    return "\n".join(text_parts)
        return str(result)

    async def call_mcp(self, method, params=None) -> object:
        hook_payload = self._tool_hook_payload(method, params)
        if hook_payload is not None:
            await emit_hook("tool_call", hook_payload)

        if method != "tools/call":
            if self._is_sse:
                return await self.call_mcp_sse(method, params)
            return await asyncio.to_thread(self.call_mcp_http, method, params)

        params = params or {}
        tool_name = str(params.get("name") or method)
        tool_arguments = params.get("arguments", {})

        try:
            with create_tool_span(
                tool_name,
                description="MCP tool call",
                parameters=tool_arguments,
                attributes={
                    "mcp.method": str(method),
                    "mcp.transport": "sse" if self._is_sse else "http",
                },
            ) as tool_span:
                if self._is_sse:
                    result = await self.call_mcp_sse(method, params)
                else:
                    result = await asyncio.to_thread(self.call_mcp_http, method, params)
                set_tool_output(tool_span, result)
        except Exception as exc:
            if hook_payload is not None:
                await emit_hook(
                    "tool_error",
                    {
                        **hook_payload,
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
            raise

        if hook_payload is not None:
            if self._is_tool_error_result(result):
                error_type = self._extract_tool_error_type(result)
                await emit_hook(
                    "tool_error",
                    {
                        **hook_payload,
                        "error": self._extract_tool_error(result),
                        "error_type": error_type,
                    },
                )
            else:
                await emit_hook(
                    "tool_result",
                    {
                        **hook_payload,
                        "tool_output": self._summarise_tool_output(result),
                    },
                )

        return result


    async def get_tools_schema(self) -> object:
        if self._is_sse:
            return await self.get_tools_schema_sse()
        else:
            return await asyncio.to_thread(self.get_tools_schema_http)


    async def call_mcp_sse(self, method, params=None):
        try:
            async with sse_client(url=self.url) as transport:
                async with ClientSession(transport[0], transport[1]) as session:
                    await session.initialize()
                    
                    if method == "tools/list":
                        response = await session.list_tools()
                        return {"tools": [t.model_dump() for t in response.tools]}
                    
                    elif method == "tools/call":
                        name = params.get("name")
                        args = params.get("arguments", {})
                        result = await session.call_tool(name, arguments=args)
                        return result.model_dump()
                    
                    return self._error_result(
                        f"Unsupported MCP method: {method}",
                        error_type="UnsupportedMethodError",
                    )

        except Exception as e:
            logger.error(f"MCP Connection Error: {e}")
            return self._error_result(str(e), error_type=type(e).__name__)

    async def get_tools_schema_sse(self):
        result = await self.call_mcp_sse("tools/list")

        if self._is_tool_error_result(result):
            logger.warning("MCP tools/list failed: %s", self._extract_tool_error(result))
            return []

        tools = []
        for t in result.get("tools", []):
            tools.append({
                "toolSpec": {
                    "name": t["name"],
                    "description": t.get("description", "No description provided"),
                    "inputSchema": {"json": t["inputSchema"]}
                }
            })
        
        logger.info(f"Loaded {len(tools)} tools.")
        return tools

    def _handle_stream_response(self, response, request_kind: str) -> object:
        last_parse_error: json.JSONDecodeError | None = None

        for line in response.iter_lines():
            if not line:
                continue
            try:
                if line.startswith("data: "):
                    data = json.loads(line[6:])
                elif line.startswith("event: "):
                    continue
                else:
                    data = json.loads(line)

                if "result" in data:
                    logger.debug("MCP %s request successful", request_kind)
                    return data["result"]

                if "error" in data:
                    error = data["error"]
                    if isinstance(error, dict):
                        error_type = error.get("type", error.get("code"))
                        message = error.get("message")
                        if message:
                            return self._error_result(
                                str(message),
                                error_type=str(error_type) if error_type is not None else "JSONRPCError",
                            )
                    return self._error_result(str(error), error_type="JSONRPCError")
            except json.JSONDecodeError as e:
                last_parse_error = e
                logger.error("Failed to parse MCP %s response: %s", request_kind, e)
                continue
            except Exception as e:
                logger.error("Unexpected error processing MCP %s response: %s", request_kind, e)
                return self._error_result(str(e), error_type=type(e).__name__)

        if last_parse_error is not None:
            return self._error_result(
                f"Failed to parse MCP {request_kind} response: {last_parse_error}",
                error_type="JSONDecodeError",
            )
        return self._error_result(
            f"MCP {request_kind} request returned no result.",
            error_type="EmptyResponseError",
        )

    def _handle_redirect_response(self, location: str) -> dict[str, object]:
        if "oauth" in location.lower():
            logger.error(
                "Check: Is your API key correct? The server is redirecting you to a login/error page. %s",
                location,
            )
            return self._error_result(
                f"MCP server redirected to a login or OAuth page: {location}",
                error_type="RedirectError",
            )

        return self._error_result(
            f"MCP server redirected to {location or 'an unexpected location'}.",
            error_type="RedirectError",
        )


    def call_mcp_http(self, method, params=None) -> object:
        headers = {
            "Accept": "application/json, text/event-stream",
            "Content-Type": "application/json"
        }
        # Fix #3: Allow users to control full authorization header format
        # Users must now include "Bearer " prefix in their token if needed
        if self.auth_key:
            headers["Authorization"] = self.auth_key

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": "1"
        }

        # Enhanced logging with sanitized headers (hide auth token)
        sanitized_headers = {k: ("***" if k == "Authorization" else v) for k, v in headers.items()}
        logger.debug(f"MCP HTTP request to {self.url} with method {method}, headers: {sanitized_headers}")

        # Use a longer timeout for MCP server calls (30 seconds)
        with httpx.Client(timeout=30.0) as mcp_client:
            # Fix #1: Try POST first, fallback to GET on 405 Method Not Allowed
            try:
                with mcp_client.stream("POST", self.url, headers=headers, json=payload) as response:
                    # Check for 405 Method Not Allowed
                    if response.status_code == 405:
                        logger.warning(f"POST method not allowed (405), falling back to GET for {self.url}")
                        # Fall through to GET fallback below
                    elif response.status_code in (301, 302):
                        location = response.headers.get('Location', '')
                        return self._handle_redirect_response(location)
                    elif response.status_code >= 400:
                        logger.error(f"MCP server returned error status {response.status_code}")
                        return self._error_result(
                            f"MCP server returned status {response.status_code} for POST request.",
                            error_type="HTTPStatusError",
                        )
                    else:
                        return self._handle_stream_response(response, "POST")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 405:
                    logger.warning(f"POST method not allowed (405), falling back to GET for {self.url}")
                    # Fall through to GET fallback
                else:
                    logger.error(f"HTTP error during POST request: {e}")
                    raise e

            # GET fallback for servers that don't support POST
            logger.info(f"Attempting GET request to {self.url} for method {method}")
            # For GET, encode params in URL query string
            params_str = json.dumps(payload)
            get_url = f"{self.url}?request={params_str}"
            
            with mcp_client.stream("GET", get_url, headers=headers) as response:
                if response.status_code in (301, 302):
                    location = response.headers.get('Location', '')
                    return self._handle_redirect_response(location)
                elif response.status_code >= 400:
                    logger.error(f"MCP server returned error status {response.status_code} for GET request")
                    return self._error_result(
                        f"MCP server returned status {response.status_code} for GET request.",
                        error_type="HTTPStatusError",
                    )

                return self._handle_stream_response(response, "GET")

        return self._error_result(
            "MCP request did not complete.",
            error_type="MCPRequestError",
        )


    def get_tools_schema_http(self) -> list[object]:
        """Dynamically pull tool definitions from your MCP server."""
        result = self.call_mcp_http("tools/list")

        if self._is_tool_error_result(result):
            logger.warning("MCP tools/list failed: %s", self._extract_tool_error(result))
            return []
        
        tools_schema = []
        for t in result.get("tools", []):
            tools_schema.append({
                "toolSpec": {
                    "name": t["name"],
                    "description": t.get("description", "No description provided"),
                    "inputSchema": {"json": t["inputSchema"]}
                }
            })

        return tools_schema
