from __future__ import annotations
import os

# pylint: disable=C0103

# Load environment variables from .env BEFORE any other imports so that
# module-level singletons (e.g. agentstudio_sdk.agentic_apps_api) can read them.
from dotenv import load_dotenv
print(os.environ.get("ENV_FILE", ".env"))
load_dotenv(dotenv_path=os.environ.get("ENV_FILE", ".env"), override=True)

# Optional AWS SDK
try:
    import boto3 as boto3_module  # pylint: disable=invalid-name  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    boto3_module = None

# Standard library

from typing import Any, cast

# Third-party
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

# First-party (project-level)
from settings import settings  # type: ignore[import-untyped]

# Local package
from .logger import get_logger
from .deepagent_executor import DeepAgentExecutor  # type: ignore
from .echo_cors_middleware import EchoCORSMiddleware  # type: ignore

logger = get_logger(__name__)


_AGENT_CARD = ExtendedAgentCard(
    name="Candidate Evaluation Agent",
    description="AI-powered agent for comprehensive candidate evaluation including resume parsing, job analysis, skill gap identification, cultural fit assessment, and match report synthesis",
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
            id="resume_parsing",
            name="Resume Parsing",
            description="Extract and analyze resume information including education, experience, skills, and achievements",
            tags=["hr", "recruitment", "resume"],
            examples=["Parse this resume for key qualifications"],
        ),
        AgentSkill(
            id="job_analysis",
            name="Job Description Analysis",
            description="Analyze job descriptions to understand core requirements and responsibilities",
            tags=["hr", "recruitment", "job"],
            examples=["Analyze this job posting for skill requirements"],
        ),
        AgentSkill(
            id="skill_gap_analysis",
            name="Skill Gap Analysis",
            description="Identify gaps and overlaps between candidate skills and job requirements",
            tags=["hr", "recruitment", "skills"],
            examples=[
                "Compare this candidate's skills against the job requirements"
            ],
        ),
        AgentSkill(
            id="culture_fit",
            name="Cultural Fit Evaluation",
            description="Assess cultural alignment between candidate and organization",
            tags=["hr", "recruitment", "culture"],
            examples=[
                "Evaluate cultural fit between this candidate and company"
            ],
        ),
        AgentSkill(
            id="candidate_evaluation",
            name="Comprehensive Candidate Evaluation",
            description="Generate detailed candidate match reports with multi-aspect analysis",
            tags=["hr", "recruitment", "evaluation"],
            examples=[
                "Provide a comprehensive evaluation of this candidate for this position"
            ],
        ),
    ],
)

_REQUEST_HANDLER = DefaultRequestHandler(
    agent_executor=DeepAgentExecutor(),
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


# Serve a spec-compliant agent-card.json explicitly to ensure
# `supportedInterfaces` and `preferredTransport` appear as expected
def _agent_card_route(_: Request):
    return JSONResponse(_AGENT_CARD.dict(), status_code=200)


app.add_route(AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])
app.add_route(
    PREV_AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"]
)


# Add Phoenix session middleware FIRST - it needs to run before CORS
# so it can access the root span before any other processing
# Add authentication middleware (optional, enabled via A2A_BEARER_TOKEN)
if AuthenticatorMiddleware is not None and os.getenv("KEYCLOAK_JWKS_URL"):
    app.add_middleware(
        AuthenticatorMiddleware, schemes=["HTTPAuthSecurityScheme"]
    )

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
