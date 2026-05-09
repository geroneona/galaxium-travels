
import json
import uuid
from typing import List, cast
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
from agentstudio_sdk.hooks import emit_hook, use_hook_context
from a2a.utils import new_task, new_text_artifact
from .deepagent_activity_logger import log_node_activity
from .agent import create_candidate_evaluation_agent
from .logger import get_logger

logger = get_logger(__name__)


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


async def _stream_working_updates(
    agent: object,
    user_input: str,
    context_id: str,
    task_id: str,
    event_queue: EventQueue,
) -> str:
    """Stream LangGraph updates, log step activity, emit working events; return final text."""
    final_text = ""
    async for chunk in agent.astream({"messages": [{"role": "user", "content": user_input}]}, stream_mode="updates"):
        for node_name, node_output in chunk.items():
            logger.debug("Stream node: %s", node_name)
            await log_node_activity(node_name, node_output)
            text = _extract_ai_text_from_node(node_output)
            if not text:
                continue
            final_text = text
            working_msg = Message(
                message_id=str(uuid.uuid4()),
                parts=cast(List[Part], [TextPart(text=text)]),
                role=Role.agent,
                context_id=context_id,
                task_id=task_id,
            )
            await event_queue.enqueue_event(
                TaskStatusUpdateEvent(
                    context_id=context_id,
                    task_id=task_id,
                    status=TaskStatus(state=TaskState.working, message=working_msg),
                    final=False,
                    metadata=None,
                )
            )
    logger.info("Agent run complete")
    return final_text


def _extract_ai_text_from_node(node_output: object) -> str:
    """Extract AI message text from a LangGraph node update dict."""
    if not isinstance(node_output, dict):
        return ""
    messages = node_output.get("messages", [])
    if not isinstance(messages, list):
        return ""
    for msg in messages:
        if "AI" not in type(msg).__name__:
            continue
        content = _extract_content(msg)
        if content:
            return content
    return ""


class DeepAgentExecutor(AgentExecutor):
    def __init__(self):
        """Initialize the executor with the candidate evaluation agent."""
        super().__init__()
        self.agent = create_candidate_evaluation_agent()

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        user_input = context.get_user_input()

        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        context_id: str = task.context_id or ""
        task_id: str = task.id or str(uuid.uuid4())

        with use_hook_context(
            framework="deepagent",
            boilerplate="deepagent/backend",
            agent_name="Candidate Evaluation Agent",
            context_id=context_id,
            task_id=task_id,
        ):
            await emit_hook("session_start", {"input": user_input})
            await emit_hook("input", {"input": user_input})
            try:
                final_text = await _stream_working_updates(
                    self.agent, user_input, context_id, task_id, event_queue
                )
            except Exception as exc:
                await emit_hook(
                    "error",
                    {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                raise

            final_text = final_text or "(No response from agent)"
            await emit_hook("output", {"output": final_text})

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                context_id=context_id,
                task_id=task_id,
                artifact=new_text_artifact(
                    name="result",
                    description="Candidate evaluation report",
                    text=final_text,
                ),
                append=False,
                last_chunk=True,
            )
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                context_id=context_id,
                task_id=task_id,
                status=TaskStatus(state=TaskState.completed),
                final=True,
                metadata=None,
            )
        )

    async def cancel(self, context, event_queue) -> None:
        status = TaskStatus(message=None, state=TaskState.canceled)
        evt = TaskStatusUpdateEvent(
            context_id=getattr(context, "context_id", "") or "",
            final=True,
            status=status,
            task_id=getattr(context, "task_id", "") or str(uuid.uuid4()),
            metadata=None,
        )
        await event_queue.enqueue_event(evt)
