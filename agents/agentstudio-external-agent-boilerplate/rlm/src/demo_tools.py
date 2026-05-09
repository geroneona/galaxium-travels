from __future__ import annotations

from typing import Any

from agentstudio_sdk.hooks import emit_hook, use_hook_context


def parse_demo_tool_request(user_text: str) -> dict[str, Any] | None:
    stripped = user_text.strip()
    if not stripped.startswith("/demo-tool "):
        return None

    command = stripped[len("/demo-tool "):].strip()
    if not command:
        return None

    if command == "context-summary":
        return {
            "tool_name": "context-summary",
            "tool_input": {},
        }

    if command.startswith("error"):
        message = command.partition(" ")[2].strip() or "Simulated demo tool failure."
        return {
            "tool_name": "error",
            "tool_input": {"message": message},
        }

    return None


def run_demo_tool(request: dict[str, Any], context_text: str) -> str:
    tool_name = request.get("tool_name")
    tool_input = request.get("tool_input", {})

    if tool_name == "context-summary":
        word_count = len(context_text.split())
        char_count = len(context_text)
        return (
            "RLM demo tool context summary:\n"
            f"- words: {word_count}\n"
            f"- characters: {char_count}"
        )

    if tool_name == "error":
        raise RuntimeError(str(tool_input.get("message", "Simulated demo tool failure.")))

    raise ValueError(f"Unknown RLM demo tool: {tool_name}")


async def run_demo_tool_with_hooks(
    request: dict[str, Any],
    context_text: str,
) -> str:
    tool_name = request.get("tool_name", "unknown")
    tool_input = request.get("tool_input", {})

    with use_hook_context(agent_name="RLMDemoTool"):
        await emit_hook(
            "tool_call",
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
            },
        )
        try:
            result = run_demo_tool(request, context_text)
        except Exception as exc:
            await emit_hook(
                "tool_error",
                {
                    "tool_name": tool_name,
                    "tool_input": tool_input,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return f"RLM demo tool '{tool_name}' failed: {exc}"

        await emit_hook(
            "tool_result",
            {
                "tool_name": tool_name,
                "tool_input": tool_input,
                "tool_output": result,
            },
        )
        return result
