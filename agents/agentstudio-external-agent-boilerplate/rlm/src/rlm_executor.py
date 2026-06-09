import uuid
from agentstudio_sdk.hooks import emit_hook, use_hook_context
from a2a.server.events import EventQueue
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    TaskStatus,
    TaskState,
    TaskStatusUpdateEvent,
    TaskArtifactUpdateEvent,
)
from a2a.utils import new_task, new_text_artifact
from .rlm_agent import rlm, rlm_context
from .demo_tools import parse_demo_tool_request, run_demo_tool_with_hooks

from .bedrock_rlm_adapter import BedrockClient
from .logger import get_logger

logger = get_logger(__name__)

def _extract_user_text(message: object) -> str:
    """Extract plain text from an A2A Message."""
    parts = getattr(message, "parts", []) or []
    texts = []
    for part in parts:
        root = getattr(part, "root", part)
        text = getattr(root, "text", None)
        if text:
            texts.append(text)
    return " ".join(texts)


async def _maybe_run_demo_tool(user_text: str) -> str | None:
    request = parse_demo_tool_request(user_text)
    if request is None:
        return None

    return await run_demo_tool_with_hooks(request, rlm_context)

class RLMExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        task = context.current_task
        if not task:
            task = new_task(context.message)
            await event_queue.enqueue_event(task)

        context_id: str = task.context_id or ""
        task_id: str = task.id or str(uuid.uuid4())

        user_text = _extract_user_text(context.message)
        logger.info("RLM query: %s", user_text)

        with use_hook_context(
            framework="rlm",
            boilerplate="rlm",
            agent_name="RLMAgent",
            context_id=context_id,
            task_id=task_id,
        ):
            await emit_hook("session_start", {"input": user_text})
            await emit_hook("input", {"input": user_text})

            demo_tool_response = await _maybe_run_demo_tool(user_text)
            if demo_tool_response is not None:
                response_text = demo_tool_response
            else:
                try:
                    result = rlm.completion(rlm_context, user_text)
                    response_text = result.response if result.response else "No response generated."
                except Exception as exc:
                    await emit_hook(
                        "error",
                        {
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    raise

            logger.info("RLM response length: %d chars", len(response_text))
            await emit_hook("output", {"output": response_text})

        await event_queue.enqueue_event(
            TaskArtifactUpdateEvent(
                context_id=context_id,
                task_id=task_id,
                artifact=new_text_artifact(
                    name="result",
                    description="Agent response",
                    text=response_text,
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
