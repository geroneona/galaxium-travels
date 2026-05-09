from __future__ import annotations

# pylint: disable=C0103

# Optional AWS SDK
try:
    import boto3 as boto3_module  # pylint: disable=invalid-name  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    boto3_module = None

# Standard library

from typing import Any, cast

# Third-party
import asyncio
import concurrent.futures
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
from starlette.middleware.base import BaseHTTPMiddleware  # type: ignore
from starlette.requests import Request
from starlette.responses import JSONResponse

from agentstudio_sdk import ExtendedAgentCard, LLM  # type: ignore
from agentstudio_sdk.hooks import load_hooks_from_env  # type: ignore[import-untyped]
from agentstudio_sdk.mcp_circuit_breaker import MCPServerWithCircuitBreaker as MCP_Server

from agentstudio_sdk.phoenix import (
    initialize_phoenix,
    PhoenixSessionMiddleware,
    PhoenixJSONRPCSessionMiddleware,
)  # type: ignore[import-untyped]
from agentstudio_sdk.agent_registration import (
    register_agent_when_ready_in_background,
)  # type: ignore[import-untyped]

try:
    from agentstudio_sdk.auth import AuthenticatorMiddleware  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional dependency
    AuthenticatorMiddleware = None

# First-party (project-level)
from config.agents import AGENTS as AGENT_CONFIG  # type: ignore[import-untyped]
from config.settings import settings  # type: ignore[import-untyped]

# Local package
from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import (
    SupervisorAgent,
    WeatherAgent,
    MealAgent,
    TermReaderAgent,
    TermWriterAgent,
)
from .a2a_integration import A2AClientAdapter
from .bootstrap import build_adapters
from .logger import get_logger
from .agentic_agent_executor import AgenticAgentExecutor  # type: ignore
from .echo_cors_middleware import EchoCORSMiddleware  # type: ignore
from .session_store import InMemorySessionStore

logger = get_logger(__name__)


def resolve_aws_region(default: str = "eu-central-1") -> str:
    """Resolve AWS region for local development.

    Preference order:
    1. `AWS_REGION` or `AWS_DEFAULT_REGION` env vars
    2. `AWS_PROFILE` via `boto3_module.session.Session(profile_name=...)`
    3. boto3 default session region
    4. fallback `default`
    """
    # 1) explicit env vars
    if settings.AWS_REGION:
        return settings.AWS_REGION

    # 2) prefer AWS_PROFILE if set
    if boto3_module is not None and settings.AWS_PROFILE:
        try:
            sess = boto3_module.session.Session(profile_name=settings.AWS_PROFILE)
            if sess.region_name:
                return sess.region_name
        except Exception:
            pass

    # 3) default boto3 session
    if boto3_module is not None:
        try:
            sess = boto3_module.session.Session()
            if sess.region_name:
                return sess.region_name
        except Exception:
            pass

    # 4) fallback
    return default


# Initialize minimal components. In production wire these via DI/container.


graph = StateGraph(AgentState)
A2A_CLIENT = A2AClientAdapter()

adapters: dict[str, LLM] = build_adapters(AGENT_CONFIG)

# Instantiate agents. Create non-supervisor agents first, then supervisor
# so it receives a populated registry.

AGENTS: dict[str, Any] = {}


def _build_mcp_server(agent_name: str, agent_cfg: dict[str, Any]) -> MCP_Server | None:
    auth_key = agent_cfg.get("auth_key")
    mcp_server_url = agent_cfg.get("mcp_server_url")

    if not auth_key:
        logger.warning("Agent '%s' configuration does not include 'auth_key'", agent_name)
    if not mcp_server_url:
        logger.warning(
            "Skipping agent '%s': configuration must include a non-empty 'mcp_server_url'",
            agent_name,
        )
        return None

    return MCP_Server(agent_cfg)


def _build_agent(agent_name: str, agent_cfg: dict[str, Any], adapter: LLM) -> Any | None:
    if agent_name == "weather":
        mcp_server = _build_mcp_server(agent_name, agent_cfg)
        if mcp_server is None:
            return None
        return WeatherAgent(adapter, graph, mcp_server)

    if agent_name == "meal":
        return MealAgent(adapter, graph)

    if agent_name == "term-reader":
        mcp_server = _build_mcp_server(agent_name, agent_cfg)
        if mcp_server is None:
            return None
        return TermReaderAgent(adapter, graph, mcp_server)

    if agent_name == "term-writer":
        mcp_server = _build_mcp_server(agent_name, agent_cfg)
        if mcp_server is None:
            return None
        return TermWriterAgent(adapter, graph, mcp_server)

    logger.warning("Unknown agent '%s' in AGENT_MODEL_MAP", agent_name)
    return None


async def initialize_agents() -> None:
    for agent_name, agent_cfg in AGENT_CONFIG.items():
        if agent_name == "supervisor":
            continue
        if not isinstance(agent_cfg, dict):
            logger.warning("Skipping agent '%s': configuration must be a dict", agent_name)
            continue

        adapter = adapters.get(agent_name)
        if adapter is None:
            logger.warning("No adapter for agent '%s'", agent_name)
            continue

        created_agent = _build_agent(agent_name, agent_cfg, adapter)
        if created_agent is None:
            continue

        try:
            await created_agent.init()
        except Exception:
            logger.exception("Skipping agent '%s': failed to initialize", agent_name)
            continue

        AGENTS[agent_name] = created_agent

        if getattr(created_agent, "mcp", False):
            logger.info(
                "For agent %s, following tools have been found: %s",
                agent_name,
                created_agent.get_tool_info(),
            )

    if "supervisor" in AGENT_CONFIG:
        sup_adapter = adapters.get("supervisor")
        if sup_adapter is not None:
            supervisor = SupervisorAgent(sup_adapter, graph, AGENTS)
            try:
                await supervisor.init()
            except Exception:
                logger.exception("Skipping agent 'supervisor': failed to initialize")
            else:
                AGENTS["supervisor"] = supervisor


async def initialize():
    load_hooks_from_env()
    await initialize_phoenix(settings.ica)
    await initialize_agents()


def _run_async_init():
    try:
        _ = asyncio.get_running_loop()

        # If we get here, there's a running loop - run in a separate thread
        def _run_in_new_loop():
            """Create a new event loop in this thread and run the initialization."""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(initialize())
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_in_new_loop)
            future.result()
    except RuntimeError as e:
        # No running event loop, safe to use asyncio.run()
        if "no running event loop" in str(e).lower() or "cannot be called" not in str(e).lower():
            asyncio.run(initialize())
        else:
            # Re-raise if it's a different RuntimeError
            raise


_run_async_init()
register_agent_when_ready_in_background(settings.ica, settings.PORT, max_retries=3, retry_delay=1.0)

# Register nodes and configure graph edges (blog-style API)
for name, agent in AGENTS.items():
    try:
        graph.add_node(name, agent.handle_message)
        graph.add_edge(name, END)
    except Exception:
        logger.exception("Failed to add graph node '%s'", name)
if "supervisor" in AGENTS:
    graph.add_conditional_edges(
        "supervisor",
        (lambda state: END if state.get("response") else state.get("target")),
    )
    entry_point: str | None = "supervisor"
else:
    # Fallback: use the first available agent as the entry point
    entry_point = next(iter(AGENTS), None)
    if entry_point is None:
        raise RuntimeError("No agents registered to set entry point for the graph")
graph.set_entry_point(cast(str, entry_point))
workflow = graph.compile()
SESSION_STORE = InMemorySessionStore(
    ttl_seconds=settings.SESSION_TTL_SECONDS,
    max_messages=settings.SESSION_MAX_MESSAGES,
)


def build_agent_skills() -> list[AgentSkill]:
    result: list[AgentSkill] = []
    for agent_key in AGENTS:
        cfg_local = AGENT_CONFIG.get(agent_key, {}) if isinstance(AGENT_CONFIG, dict) else {}
        skill_name = cfg_local.get("display_name") or cfg_local.get("name") or f"{agent_key} agent"
        description = cfg_local.get("description") or f"Agent '{agent_key}' managed by Agentic Chat"
        result.append(AgentSkill(id=agent_key, name=skill_name, description=description, tags=[]))
    return result


def _get_supported_interfaces() -> list[dict]:
    if settings.A2A_PROTOCOL == "JSONRPC":
        return [
            {
                "url": settings.agent_endpoint_url,
                "protocolBinding": "JSONRPC",
            },
        ]
    return [
        {
            "url": settings.agent_endpoint_url,
            "protocolBinding": "HTTP+JSON",
        },
    ]


def _get_app() -> Any:
    server: Any = None
    if settings.A2A_PROTOCOL == "JSONRPC":
        server = A2AStarletteApplication(agent_card=_AGENT_CARD, http_handler=_REQUEST_HANDLER)
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


_AGENT_CARD = ExtendedAgentCard(
    name="Agentic Chat Service",
    description="Boilerplate for an agentic chat",
    url=settings.agent_endpoint_url,
    version="0.1.0",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=build_agent_skills(),
    security_schemes={
        "http": HTTPAuthSecurityScheme(
            description="Bearer token authentication",
            scheme="Bearer",
        )
    },
    supported_interfaces=_get_supported_interfaces(),
    preferred_transport=settings.A2A_PROTOCOL,
    supports_authenticated_extended_card=False,
)

_REQUEST_HANDLER = DefaultRequestHandler(
    agent_executor=AgenticAgentExecutor(workflow, SESSION_STORE),
    task_store=InMemoryTaskStore(),
)

app: Any = _get_app()


async def _stop_session_store() -> None:
    await SESSION_STORE.close(reason="shutdown")


try:
    app.add_event_handler("shutdown", _stop_session_store)
except Exception:
    logger.debug("Could not register session store shutdown handler")

# Serve a spec-compliant agent-card.json explicitly to ensure
# `supportedInterfaces` and `preferredTransport` appear as expected
try:

    async def _agent_card_route(_: Request):
        return JSONResponse(_AGENT_CARD.dict(), status_code=200)

    app.add_route(AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])
    app.add_route(PREV_AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])
except Exception:
    logger.debug("Could not add explicit agent-card route; relying on SDK-provided card")

# Add middleware to ensure our agent-card overrides any SDK-provided route.
try:

    class _AgentCardMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            if request.url.path in [
                AGENT_CARD_WELL_KNOWN_PATH,
                PREV_AGENT_CARD_WELL_KNOWN_PATH,
            ]:
                return JSONResponse(_AGENT_CARD.dict(), status_code=200)
            return await call_next(request)

    app.add_middleware(_AgentCardMiddleware)
except Exception:
    logger.debug("Could not add AgentCard middleware; relying on SDK-provided card")


try:
    # Add Phoenix session middleware FIRST - it needs to run before CORS
    # so it can access the root span before any other processing
    # Add authentication middleware (optional, enabled via A2A_BEARER_TOKEN)
    if AuthenticatorMiddleware is not None:
        try:
            app.add_middleware(AuthenticatorMiddleware, schemes=["HTTPAuthSecurityScheme"])
        except Exception:
            logger.debug("Could not add AuthenticatorMiddleware; continuing without it")
    else:
        logger.debug("Could not add AuthenticatorMiddleware; continuing without it")

    app.add_middleware(
        EchoCORSMiddleware,
        allowed_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=("*",),
        allow_headers=("Authorization", "Content-Type", "Accept", "Origin"),
    )
except Exception:
    # If the built server is not a Starlette app or doesn't support add_middleware,
    # skip adding middleware to avoid raising at import time.
    logger.debug("Could not add CORS middleware to app; skipping")

try:

    async def health_check(_: Request):
        return JSONResponse({"status": "healthy"}, status_code=200)

    async def ready_check(_: Request):
        return JSONResponse({"status": "ready"}, status_code=200)

    app.add_route("/health", health_check, methods=["GET"])
    app.add_route("/ready", ready_check, methods=["GET"])
except Exception:
    logger.debug("Could not add health check route; skipping")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
