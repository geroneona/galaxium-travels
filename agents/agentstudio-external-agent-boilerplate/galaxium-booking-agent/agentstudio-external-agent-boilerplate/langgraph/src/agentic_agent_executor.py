import inspect
import uuid
from typing import Any, cast

from a2a.server.agent_execution import AgentExecutor  # type: ignore[import-untyped]
from a2a.types import (
    Message,
    TextPart,
    Role,
    TaskStatusUpdateEvent,
    TaskStatus,
    TaskState,
)  # type: ignore[import-untyped]
from openinference.instrumentation import using_session
from agentstudio_sdk.hooks import emit_hook, use_hook_context  # type: ignore[import-untyped]
from agentstudio_sdk.phoenix import create_agent_span, set_agent_output  # type: ignore[import-untyped]

from .state import AgentState
from .session_store import InMemorySessionStore
from .logger import get_logger

logger = get_logger(__name__)


class AgenticAgentExecutor(AgentExecutor):
    """Adapter executor used by the A2A request handler.

    This executor is constructed with access to the compiled workflow by the
    application `main` module, which passes the `workflow` instance into the
    constructor. The executor uses that workflow when handling incoming
    requests.
    """

    def __init__(
        self,
        workflow: Any,
        session_store: InMemorySessionStore | None = None,
    ):
        self.workflow = workflow
        self.session_store = session_store or InMemorySessionStore()

    def _get_ctx_attr(self, obj, name, default=None):
        val = getattr(obj, name, None)
        if val is not None:
            return val
        try:
            return obj.get(name, default)  # type: ignore[attr-defined]
        except Exception:
            return default

    def _get_user_text(self, context) -> str:
        try:
            user_text = context.get_user_input()
        except Exception as e:
            logger.error("Failed to get user input: %s", e)
            user_text = ""

        if user_text is None:
            return ""
        if not isinstance(user_text, str):
            logger.warning(
                "user_text is not a string, type=%s, converting",
                type(user_text),
            )
            return str(user_text)
        return user_text

    def _determine_ctx_id(self, context) -> str:
        ctx_id = self._get_ctx_attr(context, "context_id") or self._get_ctx_attr(context, "contextId")

        if not ctx_id:
            try:
                msg = getattr(context, "message", None)
                if msg:
                    ctx_id = self._get_ctx_attr(msg, "context_id") or self._get_ctx_attr(msg, "contextId")
            except Exception:
                pass

        if not ctx_id:
            ctx_id = str(uuid.uuid4())
        return ctx_id

    async def _invoke_workflow(self, initial_context: AgentState, ctx_id: str, user_text: str):
        reply_text = ""
        context = None
        with create_agent_span(ctx_id, user_text) as agent_span:
            with using_session(ctx_id):
                result = await self.workflow.ainvoke(initial_context)
                if inspect.isawaitable(result):
                    context = await result
                else:
                    context = result
                reply_text = context.get("response", "")

                if reply_text is None:
                    reply_text = ""
                if not isinstance(reply_text, str):
                    logger.warning(
                        "reply_text is not a string, type=%s, converting",
                        type(reply_text),
                    )
                    reply_text = str(reply_text)

            set_agent_output(agent_span, reply_text)

        return reply_text, context

    async def execute(self, context, event_queue) -> None:
        """Execute the agent logic for the incoming A2A `RequestContext`.

        This implementation extracts the user's text, invokes the configured
        workflow, and enqueues a `Message` event with the agent's reply.
        """
        user_text = self._get_user_text(context)

        ctx_id = self._determine_ctx_id(context)
        task_id = (
            self._get_ctx_attr(context, "task_id")
            or self._get_ctx_attr(context, "taskId")
            or str(uuid.uuid4())
        )

        workflow_context = None
        reply_text = ""

        async with self.session_store.turn(ctx_id, user_text) as turn:
            initial_context = AgentState(utterance=user_text, messages=turn.messages)

            with use_hook_context(
                framework="langgraph",
                boilerplate="langgraph",
                agent_name="LangGraphWorkflow",
                context_id=ctx_id,
                task_id=task_id,
            ):
                try:
                    if turn.is_new:
                        await emit_hook("session_start", {"input": user_text})
                    await emit_hook("input", {"input": user_text})
                    reply_text, workflow_context = await self._invoke_workflow(
                        initial_context,
                        ctx_id,
                        user_text,
                    )
                    self.session_store.append_assistant_message(ctx_id, reply_text)
                except Exception as exc:
                    await emit_hook(
                        "error",
                        {
                            "error": str(exc),
                            "error_type": type(exc).__name__,
                        },
                    )
                    raise

                await emit_hook("output", {"output": reply_text})

        task_id = self._get_ctx_attr(workflow_context, "taskId") or task_id

        parts_val = [cast(Any, TextPart(text=reply_text))]

        msg = Message(
            message_id=str(uuid.uuid4()),
            parts=parts_val,  # type: ignore[arg-type]
            role=Role.agent,
            context_id=ctx_id,
            task_id=task_id,
        )

        await event_queue.enqueue_event(msg)

    async def cancel(self, context, event_queue) -> None:
        ctx_id = getattr(context, "contextId", "") or getattr(context, "context_id", "") or ""
        if ctx_id:
            await self.session_store.end_session(ctx_id, reason="cancelled")

        status = TaskStatus(message=None, state=TaskState.canceled)
        evt = TaskStatusUpdateEvent(
            context_id=ctx_id,
            final=True,
            status=status,
            task_id=getattr(context, "taskId", None) or str(uuid.uuid4()),
            metadata=None,
        )
        await event_queue.enqueue_event(evt)
