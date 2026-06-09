
import json
import uuid
from typing import List, cast
from agentstudio_sdk.hooks import emit_hook
from a2a.server.events import EventQueue
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    Message,
    Role,
    TaskStatus,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
    TextPart,
    Part,
)
from a2a.utils import new_task, new_text_artifact
from .agent import create_candidate_evaluation_agent
from .logger import get_logger

logger = get_logger(__name__)

# ── ANSI colours (gracefully disabled on non-TTY) ──────────────────────────
_BOLD   = "\033[1m"
_CYAN   = "\033[36m"
_YELLOW = "\033[33m"
_GREEN  = "\033[32m"
_MAGENTA = "\033[35m"
_BLUE   = "\033[34m"
_RESET  = "\033[0m"


def _c(colour: str, text: str) -> str:
    """Wrap *text* in an ANSI colour code."""
    return f"{colour}{text}{_RESET}"


def _print_step(label: str, detail: str = "", *, colour: str = _CYAN) -> None:
    """Print a single agent-step line to stdout so it always appears on console."""
    prefix = _c(_BOLD + colour, f"[Agent] {label}")
    if detail:
        print(f"{prefix}  {detail}")
    else:
        print(prefix)


def _summarise_args(args: object, max_len: int = 120) -> str:
    """Return a compact one-line summary of tool arguments."""
    try:
        text = json.dumps(args, ensure_ascii=False)
    except Exception:
        text = str(args)
    return text if len(text) <= max_len else text[:max_len] + "…"


async def _log_tool_call(node_name: str, tc: object) -> None:
    """Print a single tool-call decision made by the LLM."""
    name = tc.get("name", "?") if isinstance(tc, dict) else getattr(tc, "name", "?")
    args = tc.get("args", {}) if isinstance(tc, dict) else getattr(tc, "args", {})
    await emit_hook(
        "tool_call",
        {
            "agent_name": node_name,
            "tool_name": name,
            "tool_input": args,
        },
    )
    if name == "task":
        _log_subagent_delegation(args)
    else:
        _print_step(f"  → Tool call: {_c(_BOLD, name)}", _summarise_args(args), colour=_YELLOW)


def _log_subagent_delegation(args: object) -> None:
    """Print a subagent delegation step."""
    subagent = args.get("subagent_type") if isinstance(args, dict) else "?"
    task_desc = args.get("description", "") if isinstance(args, dict) else ""
    summary = (str(task_desc)[:100] + "…") if len(str(task_desc)) > 100 else str(task_desc)
    _print_step(
        f"  → Delegate to subagent: {_c(_BOLD, str(subagent))}",
        f"task: {summary}",
        colour=_MAGENTA,
    )


async def _log_ai_message(node_name: str, msg: object) -> None:
    """Print console info for an AIMessage from *node_name*."""
    tool_calls = getattr(msg, "tool_calls", []) or []
    content = _extract_content(msg)
    _print_step(
        f"LLM call → {_c(_BOLD, node_name)}",
        f"({len(tool_calls)} tool call(s), {len(content)} chars of text)",
        colour=_BLUE,
    )
    for tc in tool_calls:
        await _log_tool_call(node_name, tc)
    if content and not tool_calls:
        preview = (content[:120] + "…") if len(content) > 120 else content
        _print_step(f"  Response from {_c(_BOLD, node_name)}", preview, colour=_GREEN)


def _is_tool_error(msg: object, raw: str) -> bool:
    status = getattr(msg, "status", None)
    if status in {"error", "failed"}:
        return True
    lowered = raw.strip().lower()
    return lowered.startswith("error") or "traceback" in lowered


async def _log_tool_message(node_name: str, msg: object) -> None:
    """Print console info for a ToolMessage (tool result)."""
    tool_name = getattr(msg, "name", "?")
    raw = _extract_content(msg)
    preview = (raw[:120] + "…") if len(raw) > 120 else raw
    hook_event = "tool_error" if _is_tool_error(msg, raw) else "tool_result"
    payload_key = "error" if hook_event == "tool_error" else "tool_output"
    # tool_input is not available on ToolMessage; use empty dict to keep
    # the payload schema consistent with other boilerplates.
    await emit_hook(
        hook_event,
        {
            "agent_name": node_name,
            "tool_name": tool_name,
            "tool_input": {},
            payload_key: raw or preview or "Tool returned no output.",
        },
    )
    _print_step(f"  ← Tool result: {_c(_BOLD, tool_name)}", preview, colour=_CYAN)

def _extract_content(msg: object) -> str:
    """Extract plain text from a LangChain/LangGraph message object."""
    if not hasattr(msg, "content"):
        return ""
    content = msg.content  # type: ignore[attr-defined]
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
        return "".join(parts)
    return ""

async def log_node_activity(node_name: str, node_output: object) -> None:
    """Inspect a LangGraph node update and print human-readable step info."""
    if not isinstance(node_output, dict):
        return
    messages = node_output.get("messages", [])
    if not isinstance(messages, list):
        return
    for msg in messages:
        msg_type = type(msg).__name__
        if "AI" in msg_type:
            await _log_ai_message(node_name, msg)
        elif "Tool" in msg_type:
            await _log_tool_message(node_name, msg)
