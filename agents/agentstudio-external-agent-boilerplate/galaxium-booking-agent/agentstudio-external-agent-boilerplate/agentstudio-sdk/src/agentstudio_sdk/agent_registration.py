"""Agent auto-registration functionality for ICA Agentic Apps.

Provides utilities to automatically register agents with the ICA platform
by polling the well-known agent card endpoint and then registering via
the Agentic Apps API.
"""

from __future__ import annotations

import asyncio
from threading import Thread
from a2a.utils.constants import AGENT_CARD_WELL_KNOWN_PATH
import httpx

from .agentic_apps_api import AgenticAppsAPI
from .settings import ICASettings
from .logger import get_logger

logger = get_logger(__name__)


async def poll_agent_card_endpoint(
    agent_url: str,
    max_retries: int = 30,
    retry_delay: float = 1.0,
    timeout: float = 5.0,
) -> bool:
    """
    Poll the well-known agent card endpoint until it's accessible.
    
    Polls the `{agent_url}/.well-known/agent-card.json` endpoint with
    exponential backoff until it receives a successful response or
    max retries is reached.
    
    Args:
        agent_url: Base URL of the agent (e.g., from ngrok tunnel)
        max_retries: Maximum number of retry attempts
        retry_delay: Initial delay between retries in seconds
        timeout: Timeout per request in seconds
        
    Returns:
        True if endpoint became accessible, False if max retries exceeded
    """
    card_endpoint = f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}"
    
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.get(card_endpoint)
                if response.status_code == 200:
                    logger.info(
                        "agent_registration: Agent card endpoint accessible at attempt %d: %s",
                        attempt + 1,
                        card_endpoint,
                    )
                    return True
        except (httpx.RequestError, asyncio.TimeoutError) as e:
            logger.debug(
                "agent_registration: Attempt %d failed for %s: %s",
                attempt + 1,
                card_endpoint,
                str(e),
            )
        
        if attempt < max_retries - 1:
            await asyncio.sleep(retry_delay * (2 ** min(attempt // 5, 3)))  # Exponential backoff, capped at 8x
    
    logger.warning(
        "agent_registration: Agent card endpoint not accessible after %d attempts: %s",
        max_retries,
        card_endpoint,
    )
    return False


async def register_agent_when_ready(settings: ICASettings, port: int, max_retries: int = 30, retry_delay: float = 1.0) -> dict:
    """
    Automatically register an agent by polling its card endpoint then registering.
    
    This function:
    1. Polls the agent's well-known agent card endpoint until accessible
    2. Registers the agent with the ICA Agentic Apps API
    
    Args:
        settings: ICASettings instance with agent and ICA credentials

    Returns:
        Response containing agent registration status and metadata
        
    Raises:
        RuntimeError: If agent card endpoint is not accessible after polling
        httpx.HTTPStatusError: If agent registration fails
    """

    logger.info(
        "agent_registration: Starting auto-registration for agent at %s",
        settings.agent_url,
    )
    
    # Poll the agent card endpoint
    card_accessible = await poll_agent_card_endpoint(
        agent_url=f"http://localhost:{port}",
        max_retries=max_retries,
        retry_delay=retry_delay,
    )
    
    if not card_accessible:
        msg = (
            f"Agent card endpoint at {settings.agent_url}{AGENT_CARD_WELL_KNOWN_PATH} "
            f"did not become accessible after {max_retries} attempts"
        )
        logger.error("agent_registration: %s", msg)
        raise RuntimeError(msg)
    
    # Register the agent via Agentic Apps API
    logger.info(
        "agent_registration: Agent card accessible, registering agent with app_id=%s",
        settings.app_id,
    )
    
    api = AgenticAppsAPI(
        api_token=settings.ica_token,
        team_id=settings.team_id,
        user_id=settings.user_id,
    )
    
    registration_result = await api.register_agent(
        app_id=settings.app_id,
        app_name=settings.app_name,
        agent_url=settings.agent_url,
        agent_type=settings.agent_type,
        provider=settings.provider,
    )
    
    logger.info(
        "agent_registration: Agent registration completed with status: %s, %s",
        registration_result.get("status"), registration_result.get("status_message")
    )
    
    return registration_result


def register_agent_when_ready_in_background(settings: ICASettings, port: int, max_retries: int = 30, retry_delay: float = 1.0) -> dict:
    if settings.register_agent:
        def _run_registration():
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            return new_loop.run_until_complete(register_agent_when_ready(settings, port, max_retries, retry_delay))
        t = Thread(target=_run_registration)
        t.start()
