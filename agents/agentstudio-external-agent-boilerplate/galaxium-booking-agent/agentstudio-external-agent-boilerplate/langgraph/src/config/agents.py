"""Agent -> model alias mapping.

This file is intended to be edited by users of the boilerplate to select
which model alias each agent should use. Keeping it separate from
`config/models.py` makes `models.py` stable while `agents.py` is user-editable.
"""

from __future__ import annotations
import os

from typing import Dict
from config.settings import settings  # type: ignore[import-untyped]

PREFERRED_PROVIDER = os.environ.get("PREFERRED_PROVIDER")
PREFERRED_MODEL = os.environ.get("PREFERRED_MODEL")

AGENTS: Dict[str, dict] = {
    "supervisor": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-5.1",
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Supervisor Agent",
        "description": "Supervisor agent that coordinates and routes messages",
    },
    "weather": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-4o",  # Using available model from ICA provider
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Weather Agent",
        "description": "Provides weather information",
        "mcp_server_url": settings.WA_MCP_SERVER_URL,
        "auth_key": settings.WA_AUTHORIZATION,
    },
    "booking": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-4o",  # Using available model from ICA provider
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Booking Agent",
        "description": "Books interplanetary flights, manages reservations, and handles travel bookings for Galaxium Travels",
        "mcp_server_url": settings.WA_MCP_SERVER_URL,
        "auth_key": settings.WA_AUTHORIZATION,
    },
    "meal": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-4o",  # Using available model from ICA provider
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Meal Agent",
        "description": "Provides meal and food suggestions",
    },
    "term-reader": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-4o",
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Term Reader Agent",
        "description": "Retrieves and searches terms from Rulebook AI",
        "mcp_server_url": settings.RULEBOOK_MCP_SERVER_URL,
        "auth_key": f"Bearer {settings.RULEBOOK_BEARER_TOKEN}",
    },
    "term-writer": {
        "provider": PREFERRED_PROVIDER or "azure",  # Falls back to "ica" provider
        "model": PREFERRED_MODEL or "gpt-4o",
        # "provider": "aws",
        # "model": "claude-sonnet",
        "name": "Term Writer Agent",
        "description": "Creates new terms in Rulebook AI",
        "mcp_server_url": settings.RULEBOOK_MCP_SERVER_URL,
        "auth_key": f"Bearer {settings.RULEBOOK_BEARER_TOKEN}",
    },
}

__all__ = ["AGENTS"]
