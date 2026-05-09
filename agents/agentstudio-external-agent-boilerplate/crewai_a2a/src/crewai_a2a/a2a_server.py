"""This file serves as the main entry point for the application.

It initializes the A2A server, defines the agent's capabilities,
and starts the server to handle incoming requests.
"""

import logging
import os
import sys
import asyncio
import concurrent.futures
import uvicorn

from dotenv import load_dotenv
print(os.environ.get("ENV_FILE", ".env"))
load_dotenv(dotenv_path=os.environ.get("ENV_FILE", ".env"), override=True)

from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentSkill,
    HTTPAuthSecurityScheme,
)
from a2a.server.apps import A2AStarletteApplication
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH, PREV_AGENT_CARD_WELL_KNOWN_PATH
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.requests import Request

from agentstudio_sdk import ExtendedAgentCard
from agentstudio_sdk.hooks import load_hooks_from_env
from agentstudio_sdk.phoenix import initialize_phoenix, PhoenixJSONRPCSessionMiddleware
from agentstudio_sdk.agent_registration import register_agent_when_ready_in_background
from agentstudio_sdk.settings import ICASettings
from agentstudio_sdk.auth import AuthenticatorMiddleware

from crewai_a2a.agent_executor import CrewAgentExecutor
from crewai_a2a.agents import bedrock_llm


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


PORT = int(os.environ.get("PORT", 8000))
HOST = os.environ.get("HOST", f"http://localhost:{PORT}/")
PUBLIC_AGENT_URL = os.environ.get("PUBLIC_AGENT_URL", HOST)
RPC_PATH = os.environ.get("RPC_PATH", "/v1/rpc")
RPC_URL = f"{PUBLIC_AGENT_URL.rstrip('/')}{RPC_PATH}"


async def initialize(ica_settings: ICASettings):
    load_hooks_from_env()
    await initialize_llm()
    await initialize_phoenix(ica_settings)


async def initialize_llm():
    # Eagerly initialize any module-level LLMs used by agents (so ICA discovery
    # and provider adapters are ready before handling requests).
    try:
        await bedrock_llm.init()
        logger.info("Initialized module-level LLM (bedrock_llm)")
    except Exception as _e:
        logger.warning("Failed to initialize bedrock_llm at startup: %s", _e)


def _run_async_init(ica_settings: ICASettings):
    # Check if there's already a running event loop
    try:
        asyncio.get_running_loop()

        # If we get here, there's a running loop - run in a separate thread
        def _run_in_new_loop():
            """Create a new event loop in this thread and run the initialization."""
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            try:
                return new_loop.run_until_complete(initialize(ica_settings))
            finally:
                new_loop.close()

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_run_in_new_loop)
            future.result()
    except RuntimeError as e:
        # No running event loop, safe to use asyncio.run()
        if "no running event loop" in str(e).lower() or "cannot be called" not in str(e).lower():
            asyncio.run(initialize(ica_settings))
        else:
            # Re-raise if it's a different RuntimeError
            raise


def build_agent_card() -> ExtendedAgentCard:

    skills = [
        AgentSkill(
            id="crew",
            name="CrewAI Boilerplate",
            description="Run the crew",
            tags=["crew"],
            examples=["run"],
        )
    ]

    card = ExtendedAgentCard(
        name=os.environ.get("AGENT_NAME", "CrewAI A2A agent"),
        description=os.environ.get("AGENT_DESC", "CrewAI A2A agent"),
        url=RPC_URL,
        preferred_transport="JSONRPC",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=skills,
        supports_authenticated_extended_card=False,
        security_schemes={
            "http": HTTPAuthSecurityScheme(
                description="Bearer token authentication",
                scheme="Bearer",
            )
        },
        supported_interfaces=[
            {
                "url": RPC_URL,
                "protocolBinding": "JSONRPC",
            },
        ],
        preferredTransport="JSONRPC",
    )
    return card


ica_settings = ICASettings.from_env(PUBLIC_AGENT_URL)
_run_async_init(ica_settings)
register_agent_when_ready_in_background(ica_settings, PORT, max_retries=3, retry_delay=1.0)

agent_card = build_agent_card()

request_handler = DefaultRequestHandler(
    agent_executor=CrewAgentExecutor(),
    task_store=InMemoryTaskStore(),
)
server = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler).build(rpc_url=RPC_PATH)
# Add optional authentication middleware (enabled by env var)
try:
    server.add_middleware(AuthenticatorMiddleware, schemes=["HTTPAuthSecurityScheme"])
except Exception:
    logger.debug("Could not add AuthenticatorMiddleware; continuing without it")

server.add_middleware(PhoenixJSONRPCSessionMiddleware, rpc_path=RPC_PATH)

# Configure CORS for development (allow all unless specified)
allowed_origins = ["*"]
if os.environ.get("ALLOWED_ORIGINS") is not None:
    allowed_origins = os.environ.get("ALLOWED_ORIGINS").split(",")

server.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin"],
)


# Serve agent-card explicitly via route so other middleware (CORS, etc.) runs.
async def _agent_card_route(_: Request):
    return JSONResponse(agent_card.dict(), status_code=200)


server.add_route(AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])
server.add_route(PREV_AGENT_CARD_WELL_KNOWN_PATH, _agent_card_route, methods=["GET"])


# add healthcheck endpoints
async def health_check(_: Request):
    return JSONResponse({"status": "healthy"}, status_code=200)


async def ready_check(_: Request):
    return JSONResponse({"status": "ready"}, status_code=200)


server.add_route("/health", health_check, methods=["GET"])
server.add_route("/ready", ready_check, methods=["GET"])


def serve_a2a():
    """Entry point for the A2A server."""
    try:
        uvicorn.run(server, host="0.0.0.0", port=PORT)
    except Exception as e:
        logger.error(f"An error occurred during server startup: {e}")
        sys.exit(1)


if __name__ == "__main__":
    serve_a2a()
