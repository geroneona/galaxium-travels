from __future__ import annotations
import os

from dotenv import load_dotenv
print(os.environ.get("ENV_FILE", ".env"))
load_dotenv(dotenv_path=os.environ.get("ENV_FILE", ".env"), override=True)

from typing import Any

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.apps.rest import A2ARESTFastAPIApplication  # type: ignore[import-untyped]
from a2a.server.request_handlers import DefaultRequestHandler  # type: ignore[import-untyped]
from a2a.server.tasks import InMemoryTaskStore  # type: ignore[import-untyped]
from a2a.types import (
    AgentCapabilities,
    AgentSkill,
    HTTPAuthSecurityScheme,
)  # type: ignore[import-untyped]
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    PREV_AGENT_CARD_WELL_KNOWN_PATH,
)

from starlette.requests import Request
from starlette.responses import JSONResponse

from agentstudio_sdk import ExtendedAgentCard, initialize_ica
from agentstudio_sdk.phoenix import (
    PhoenixSessionMiddleware,
    PhoenixJSONRPCSessionMiddleware,
)  # type: ignore[import-untyped]

try:
    from agentstudio_sdk.auth import AuthenticatorMiddleware  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    AuthenticatorMiddleware = None

from settings import settings  # type: ignore[import-untyped]

from .logger import get_logger
from .rlm_executor import RLMExecutor
from .echo_cors_middleware import EchoCORSMiddleware  # type: ignore

logger = get_logger(__name__)


_AGENT_CARD = ExtendedAgentCard(
    name="RLM Agent",
    description="Recursive Language Model agent that answers questions about large texts. Demo uses Clarissa, one of the longest novels in English literature.",
    version="0.1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    url=settings.agent_endpoint_url,
    preferred_transport=settings.a2a_protocol,
    supports_authenticated_extended_card=False,
    capabilities=AgentCapabilities(streaming=True),
    supported_interfaces=[{"url": settings.agent_endpoint_url, "protocolBinding": settings.a2a_protocol}],
    security_schemes=({
        "http": HTTPAuthSecurityScheme(description="Bearer token authentication", scheme="Bearer")
    } if os.getenv("KEYCLOAK_JWKS_URL") else None),
    skills=[
        AgentSkill(
            id="rlm_qa",
            name="Long-context Q&A",
            description="Answer questions about large documents using Recursive Language Models",
            tags=["rlm", "qa", "long-context"],
            examples=["Who is Clarissa's best friend?"],
        ),
    ],
)

_REQUEST_HANDLER = DefaultRequestHandler(
    agent_executor=RLMExecutor(),
    task_store=InMemoryTaskStore(),
)


def _get_app() -> Any:
    server: Any = None
    if settings.a2a_protocol == "JSONRPC":
        server = A2AStarletteApplication(
            agent_card=_AGENT_CARD, http_handler=_REQUEST_HANDLER
        )
        built_app = server.build(rpc_url=settings.agent_endpoint_path)
        built_app.add_middleware(
            PhoenixJSONRPCSessionMiddleware,
            rpc_path=settings.agent_endpoint_path,
        )
        return built_app

    server = A2ARESTFastAPIApplication(
        agent_card=_AGENT_CARD,
        http_handler=_REQUEST_HANDLER,
    )
    built_app = server.build()
    built_app.add_middleware(PhoenixSessionMiddleware)
    return built_app


app: Any = _get_app()


def _agent_card_route(_: Request):
    return JSONResponse(_AGENT_CARD.dict(), status_code=200)


app.add_route(AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])
app.add_route(
    PREV_AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"]
)

if AuthenticatorMiddleware is not None and (os.getenv("KEYCLOAK_JWKS_URL") or os.getenv("A2A_BEARER_TOKEN")):
    app.add_middleware(AuthenticatorMiddleware, schemes=["HTTPAuthSecurityScheme"])

app.add_middleware(
    EchoCORSMiddleware,
    allowed_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=("*",),
    allow_headers=("Authorization", "Content-Type", "Accept", "Origin"),
)


async def health_check(_: Request):
    return JSONResponse({"status": "healthy"}, status_code=200)


async def ready_check(_: Request):
    return JSONResponse({"status": "ready"}, status_code=200)


app.add_route("/health", health_check, methods=["GET"])
app.add_route("/ready", ready_check, methods=["GET"])


initialize_ica(settings.ica, settings.PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
