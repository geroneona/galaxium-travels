"""Phoenix-related tracing utilities and middleware for the shared SDK.

This module is intended to be installed as the `agentstudio_sdk` package and
consumed by multiple boilerplates. It avoids importing project-local
logger helpers to keep the SDK hermetic.
"""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response as StarletteResponse

from opentelemetry.util.types import AttributeValue
from openinference.semconv.trace import SpanAttributes, MessageAttributes
from openinference.instrumentation import (
    TracerProvider,
    get_input_attributes,
    get_llm_attributes,
    get_output_attributes,
    get_tool_attributes,
)
try:
    from phoenix.otel import register as _phoenix_register
except Exception as exc:  # pragma: no cover - optional dependency mismatch
    _phoenix_register = None
    _phoenix_register_import_error = exc
else:
    _phoenix_register_import_error = None

from .agentic_apps_api import agentic_apps_api
from .settings import ICASettings

from .logger import get_logger

logger = get_logger(__name__)


def _get_tracer(name: str = __name__):
    global PHOENIX_TRACER_PROVIDER
    if not PHOENIX_TRACER_PROVIDER:
        return None
    return PHOENIX_TRACER_PROVIDER.get_tracer(name)


def _set_span_attributes(span, attributes: dict[str, AttributeValue] | None) -> None:
    if not (span and span.is_recording() and attributes):
        return
    span.set_attributes(attributes)


class PhoenixSessionMiddleware(BaseHTTPMiddleware):
    """Sets Phoenix session/message attributes on root span for Sessions view.

    This middleware creates a root span and sets session/input/output
    attributes that Phoenix uses to display conversations.
    """

    def _extract_session_and_input(
        self, data: dict
    ) -> tuple[str | None, str | None]:
        session_id = (
            data.get("contextId")
            or data.get("message", {}).get("contextId")
            or None
        )

        user_input = None
        parts = data.get("message", {}).get("parts", [])
        if parts and isinstance(parts, list):
            for part in parts:
                if isinstance(part, dict) and part.get("text"):
                    user_input = part.get("text")
                    break

        if not user_input:
            content = data.get("message", {}).get("content", [])
            if content and isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("text"):
                        user_input = item.get("text")
                        break

        return session_id, user_input

    def _extract_response_text(self, data: dict) -> str | None:
        parts = data.get("message", {}).get("parts", [])
        if parts:
            for part in parts:
                if isinstance(part, dict) and part.get("text"):
                    return part.get("text")
        content = data.get("message", {}).get("content", [])
        if content:
            text_list = [part.get("text", "") for part in content]
            return "\n".join(text_list)
        return None

    def _set_input_attributes(
        self, span, session_id: str | None, user_input: str
    ) -> None:
        if not (span and span.is_recording()):
            return

        if session_id is not None:
            span.set_attribute(SpanAttributes.SESSION_ID, str(session_id))
        span.set_attribute(SpanAttributes.INPUT_VALUE, str(user_input))
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")

        input_msg_base = f"{SpanAttributes.LLM_INPUT_MESSAGES}.0"
        span.set_attribute(
            f"{input_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "user"
        )
        span.set_attribute(
            f"{input_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
            str(user_input),
        )

    def _set_output_attributes(self, span, agent_response: str) -> None:
        if not (span and span.is_recording()):
            return

        span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(agent_response))
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "text/plain")

        output_msg_base = f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0"
        span.set_attribute(
            f"{output_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "assistant"
        )
        span.set_attribute(
            f"{output_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
            str(agent_response),
        )

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.endswith("/message:send"):
            return await call_next(request)

        session_id = None
        user_input = None
        body = b""

        try:
            body = await request.body()
            if body:
                data = json.loads(body)
                session_id, user_input = self._extract_session_and_input(data)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "PhoenixSessionMiddleware: Failed to parse request: %s", exc
            )

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)

        # tracer = trace.get_tracer(__name__)
        global PHOENIX_TRACER_PROVIDER
        if PHOENIX_TRACER_PROVIDER:
            tracer = PHOENIX_TRACER_PROVIDER.get_tracer(__name__)
            with tracer.start_as_current_span(
                "http_request",
                attributes={
                    "http.method": request.method,
                    "http.url": str(request.url),
                },
            ) as root_span:
                if user_input:
                    self._set_input_attributes(
                        root_span, session_id, user_input
                    )

                response = await call_next(request)

                try:
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk

                    if response_body:
                        response_data = json.loads(response_body)

                        response_context_id = response_data.get(
                            "message", {}
                        ).get("contextId", None)
                        if (
                            session_id is None
                            and response_context_id is not None
                        ):
                            root_span.set_attribute(
                                SpanAttributes.SESSION_ID, response_context_id
                            )

                        agent_response = self._extract_response_text(
                            response_data
                        )
                        if agent_response:
                            self._set_output_attributes(
                                root_span, agent_response
                            )

                    return StarletteResponse(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        "PhoenixSessionMiddleware: Failed to process response: %s",
                        exc,
                    )
                    return response
        else:
            return await call_next(request)


class PhoenixJSONRPCSessionMiddleware(BaseHTTPMiddleware):
    """Sets Phoenix session/message attributes on root span for Sessions view.

    This middleware creates a root span and sets session/input/output
    attributes that Phoenix uses to display conversations.

    This middleware is designed to work with JSONRPC A2A protocol binding.
    """

    rpc_path = "/"

    def __init__(self, app, rpc_path: str):
        super().__init__(app)
        self.rpc_path = rpc_path

    def _extract_response_text(self, data: dict) -> str | None:
        content = data.get("result", {}).get("parts", [])
        if content:
            text_list = [part.get("text", "") for part in content]
            return "\n".join(text_list)
        return None

    def _set_input_attributes(
        self, span, session_id: str | None, user_input: str
    ) -> None:
        if not (span and span.is_recording()):
            return

        if session_id is not None:
            span.set_attribute(SpanAttributes.SESSION_ID, str(session_id))
        span.set_attribute(SpanAttributes.INPUT_VALUE, str(user_input))
        span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")

        input_msg_base = f"{SpanAttributes.LLM_INPUT_MESSAGES}.0"
        span.set_attribute(
            f"{input_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "user"
        )
        span.set_attribute(
            f"{input_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
            str(user_input),
        )

    def _set_output_attributes(self, span, agent_response: str) -> None:
        if not (span and span.is_recording()):
            return

        span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(agent_response))
        span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "text/plain")

        output_msg_base = f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0"
        span.set_attribute(
            f"{output_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "assistant"
        )
        span.set_attribute(
            f"{output_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
            str(agent_response),
        )

    async def dispatch(self, request: Request, call_next):
        if request.url.path != self.rpc_path:
            return await call_next(request)

        session_id = None
        user_input = None
        body = None

        try:
            body_bytes = await request.body()
            if body_bytes:
                body = json.loads(body_bytes)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception(
                "PhoenixSessionMiddleware: Failed to parse request: %s", exc
            )

        if body["method"] != "message/send":
            return await call_next(request)

        session_id = (
            body.get("params", {}).get("message", {}).get("contextId", None)
        )
        input_parts = body.get("params", {}).get("message", {}).get("parts", [])
        user_input = "\n".join([part.get("text", "") for part in input_parts])

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        request = Request(request.scope, receive)

        # tracer = trace.get_tracer(__name__)
        global PHOENIX_TRACER_PROVIDER
        if PHOENIX_TRACER_PROVIDER:
            tracer = PHOENIX_TRACER_PROVIDER.get_tracer(__name__)
            with tracer.start_as_current_span(
                "jsonrpc_request",
                attributes={
                    "jsonrpc.method": body["method"],
                    "jsonrpc.url": str(request.url),
                },
            ) as root_span:
                if user_input:
                    self._set_input_attributes(
                        root_span, session_id, user_input
                    )

                response = await call_next(request)

                try:
                    response_body = b""
                    async for chunk in response.body_iterator:
                        response_body += chunk

                    if response_body:
                        response_data = json.loads(response_body)

                        response_context_id = response_data.get(
                            "result", {}
                        ).get("contextId", None)
                        if (
                            session_id is None
                            and response_context_id is not None
                        ):
                            root_span.set_attribute(
                                SpanAttributes.SESSION_ID, response_context_id
                            )

                        agent_response = self._extract_response_text(
                            response_data
                        )
                        if agent_response:
                            self._set_output_attributes(
                                root_span, agent_response
                            )

                    return StarletteResponse(
                        content=response_body,
                        status_code=response.status_code,
                        headers=dict(response.headers),
                        media_type=response.media_type,
                    )
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception(
                        "PhoenixSessionMiddleware: Failed to process response: %s",
                        exc,
                    )
                    return response
        else:
            # When Phoenix is not enabled, simply forward the request and
            # return the downstream response. Previously this assigned to
            # `response` but did not return it, causing a `None` to be
            # propagated back to Starlette which led to "'NoneType' object is
            # not callable" errors. Return the response directly.
            return await call_next(request)


@contextmanager
def create_agent_span(session_id: str, user_input: str):
    """Context manager that creates an `agent` span and sets input attributes.

    Usage:
        with create_agent_span(session_id, user_input) as span:
            # run workflow, then optionally set output attrs with set_agent_output
    """
    tracer = _get_tracer(__name__)
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(
        "agent",
        openinference_span_kind="agent",
    ) as span:
        if session_id and user_input:
            span.set_attribute(SpanAttributes.SESSION_ID, str(session_id))
            span.set_attribute(SpanAttributes.INPUT_VALUE, str(user_input))
            span.set_attribute(SpanAttributes.INPUT_MIME_TYPE, "text/plain")

            input_msg_base = f"{SpanAttributes.LLM_INPUT_MESSAGES}.0"
            span.set_attribute(
                f"{input_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "user"
            )
            span.set_attribute(
                f"{input_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
                str(user_input),
            )

        yield span


def set_agent_output(span, reply_text: str) -> None:
    """Set output attributes on an `agent` span."""
    if not (span and span.is_recording()):
        return
    span.set_attribute(SpanAttributes.OUTPUT_VALUE, str(reply_text))
    span.set_attribute(SpanAttributes.OUTPUT_MIME_TYPE, "text/plain")

    output_msg_base = f"{SpanAttributes.LLM_OUTPUT_MESSAGES}.0"
    span.set_attribute(
        f"{output_msg_base}.{MessageAttributes.MESSAGE_ROLE}", "assistant"
    )
    span.set_attribute(
        f"{output_msg_base}.{MessageAttributes.MESSAGE_CONTENT}",
        str(reply_text),
    )


@contextmanager
def create_llm_span(
    span_name: str,
    *,
    model_name: str | None = None,
    provider: str | None = None,
    input_value: Any | None = None,
    input_messages: list[dict[str, Any]] | None = None,
    invocation_parameters: dict[str, Any] | str | None = None,
    tools: list[dict[str, Any]] | None = None,
    attributes: dict[str, AttributeValue] | None = None,
):
    """Create an OpenInference `llm` span for a model invocation."""
    tracer = _get_tracer(__name__)
    if tracer is None:
        yield None
        return

    llm_attributes = dict(
        get_llm_attributes(
            model_name=model_name,
            provider=provider,
            invocation_parameters=invocation_parameters,
            input_messages=input_messages,
            tools=tools,
        )
    )
    if input_value is not None:
        llm_attributes.update(get_input_attributes(input_value))
    if attributes:
        llm_attributes.update(attributes)

    with tracer.start_as_current_span(
        span_name,
        openinference_span_kind="llm",
        attributes=llm_attributes,
    ) as span:
        yield span


def set_llm_output(
    span,
    *,
    output_value: Any | None = None,
    output_messages: list[dict[str, Any]] | None = None,
    token_count: dict[str, int] | None = None,
    attributes: dict[str, AttributeValue] | None = None,
) -> None:
    """Set output attributes on an `llm` span."""
    span_attributes: dict[str, AttributeValue] = {}
    if output_value is not None:
        span_attributes.update(get_output_attributes(output_value))
    if output_messages is not None or token_count is not None:
        span_attributes.update(
            get_llm_attributes(
                output_messages=output_messages,
                token_count=token_count,
            )
        )
    if attributes:
        span_attributes.update(attributes)
    _set_span_attributes(span, span_attributes)


@contextmanager
def create_tool_span(
    tool_name: str,
    *,
    description: str | None = None,
    parameters: dict[str, Any] | str | None = None,
    span_name: str | None = None,
    attributes: dict[str, AttributeValue] | None = None,
):
    """Create an OpenInference `tool` span for a tool invocation."""
    tracer = _get_tracer(__name__)
    if tracer is None:
        yield None
        return

    tool_attributes = dict(
        get_tool_attributes(
            name=tool_name,
            description=description,
            parameters=parameters or {},
        )
    )
    if attributes:
        tool_attributes.update(attributes)

    with tracer.start_as_current_span(
        span_name or tool_name,
        openinference_span_kind="tool",
        attributes=tool_attributes,
    ) as span:
        yield span


def set_tool_output(
    span,
    output_value: Any,
    *,
    attributes: dict[str, AttributeValue] | None = None,
) -> None:
    """Set output attributes on a `tool` span."""
    span_attributes = dict(get_output_attributes(output_value))
    if attributes:
        span_attributes.update(attributes)
    _set_span_attributes(span, span_attributes)


PHOENIX_TRACER_PROVIDER: TracerProvider = None


# Auto-register Phoenix OTEL tracer when a collector endpoint is configured.
# This keeps application code free of direct Phoenix/OpenTelemetry setup.
async def initialize_phoenix(ica_settings: ICASettings) -> None:
    use_observability = os.getenv("ICA_OBSERVABILITY", "false").lower() in (
        "true",
        "1",
        "yes",
    )
    if use_observability:
        try:
            phoenix_collector_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
            phoenix_api_key = os.getenv("PHOENIX_API_KEY")

            if (
                phoenix_collector_endpoint is None
                and ica_settings.team_id is not None
                and ica_settings.ica_token is not None
            ):
                logger.info(
                    "agentstudio_sdk.phoenix: ICA_TEAM_ID and ICA_TOKEN set, loading Phoenix credentials from platform-settings endpoint"
                )

                platform_settings = (
                    await agentic_apps_api.get_platform_settings()
                )
                phoenix_collector_endpoint = platform_settings.get(
                    "observability", {}
                ).get("endpoint")
                phoenix_api_key = platform_settings.get(
                    "observability", {}
                ).get("token")

            if phoenix_collector_endpoint:
                try:
                    global PHOENIX_TRACER_PROVIDER
                    if _phoenix_register is None:
                        raise RuntimeError(
                            "phoenix.otel register import failed"
                        ) from _phoenix_register_import_error
                    PHOENIX_TRACER_PROVIDER = _phoenix_register(
                        verbose=False,
                        auto_instrument=False,
                        endpoint=phoenix_collector_endpoint,
                        api_key=phoenix_api_key,
                        project_name=ica_settings.app_id,
                    )
                except Exception:
                    logger.exception(
                        "agentstudio_sdk.phoenix: failed to register phoenix.otel tracer"
                    )
        except Exception:
            # Be defensive: any import-time failure must not prevent app startup.
            logger.debug(
                "agentstudio_sdk.phoenix: auto-registration skipped or failed"
            )
