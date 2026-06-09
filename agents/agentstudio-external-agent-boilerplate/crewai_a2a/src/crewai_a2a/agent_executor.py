import asyncio
import inspect
import uuid
from contextvars import copy_context
from typing import List, cast
from a2a.server.events import EventQueue
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.types import (
    Message,
    Role,
    TaskStatus,
    TaskState,
    TaskStatusUpdateEvent,
    TextPart,
    Part,
)
from agentstudio_sdk.hooks import emit_hook, use_hook_context
from crewai_a2a.flow import BoilerplateFlow


class CrewAgentExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        try:
            user_input = context.get_user_input()
        except Exception:
            user_input = ""

        context_id = getattr(context, "context_id", "") or str(uuid.uuid4())
        task_id = getattr(context, "task_id", "") or str(uuid.uuid4())

        with use_hook_context(
            framework="crewai",
            boilerplate="crewai_a2a",
            agent_name="CrewAIFlow",
            context_id=context_id,
            task_id=task_id,
        ):
            await emit_hook("session_start", {"input": user_input})
            await emit_hook("input", {"input": user_input})

            flow = BoilerplateFlow()

            # Run crew kickoff in threadpool to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            call_context = copy_context()
            try:
                result = await loop.run_in_executor(
                    None,
                    lambda: call_context.run(
                        flow.kickoff,
                        inputs={"user_input": user_input},
                    ),
                )
            except Exception as exc:
                await emit_hook(
                    "error",
                    {
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )
                result = f"Crew execution failed: {exc}"

            if inspect.isawaitable(result):
                result = await result

            response = str(flow.state.answer or result or "")
            await emit_hook("output", {"output": response})

        msg = Message(
            message_id=str(uuid.uuid4()),
            parts=cast(List[Part], [TextPart(text=response)]),
            role=Role.agent,
            context_id=context_id,
            task_id=task_id,
        )

        await event_queue.enqueue_event(msg)

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
