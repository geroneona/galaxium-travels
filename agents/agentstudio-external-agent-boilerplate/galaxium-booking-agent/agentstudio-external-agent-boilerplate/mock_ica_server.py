"""Mock ICA Agentic Apps API server for local testing and development.

This server provides mock endpoints that mimic the real ICA API responses,
allowing local development and testing without hitting the actual platform.

Usage:
    python mock_ica_server.py
    # Server runs on http://localhost:8888

Environment variables:
    ICA_MOCK_PORT: Port to run server on (default: 8888)
"""

import os
import json
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Header, Form
from fastapi.responses import JSONResponse
import uvicorn


# Initialize FastAPI app
app = FastAPI(
    title="Mock ICA Agentic Apps API",
    description="Mock server for ICA Agentic Apps API testing",
    version="1.0.0",
)

# In-memory storage for mock data
_apps_store: Dict[str, Dict[str, Any]] = {}
_agents_store: Dict[str, Dict[str, Any]] = {}

# Mock configuration data
MOCK_PROVIDER_CONFIGS = {
    "providers": [
        {
            "provider": "aws",
            "provider_id": 1,
            "frameworks": ["aws bedrock", "autogen", "strands"],
            "models": [
                {
                    "modelName": "Claude Opus 4",
                    "provider": "AWS",
                    "modelId": "arn:aws:bedrock:us-east-1:123456789:inference-profile/claude-opus",
                    "config": {"temperature": 0.7, "max_tokens": 2048},
                }
            ],
            "chatModelConfig": {
                "models": [
                    {
                        "modelId": "arn:aws:bedrock:us-east-1::foundation-model/amazon.nova-lite",
                        "modelName": "Amazon Nova Lite",
                        "providerName": "Amazon",
                        "inputModalities": ["TEXT", "IMAGE"],
                        "outputModalities": ["TEXT"],
                        "customizationsSupported": [],
                        "inferenceTypesSupported": ["ON_DEMAND"],
                    }
                ]
            },
            "isDefaultChatModel": False,
            "providerConfig": {
                "region": "us-east-1",
                "accountId": "123456789",
                "maxAgentLimit": 1000,
            },
        },
        {
            "provider": "azure",
            "provider_id": 2,
            "frameworks": ["azure ai foundry", "autogen", "strands"],
            "models": [
                {
                    "modelName": "gpt-4o",
                    "provider": "OpenAI",
                    "modelId": "gpt-4o",
                    "config": {"temperature": 0.7, "max_tokens": 2048},
                }
            ],
            "chatModelConfig": {
                "models": [
                    {
                        "modelId": "gpt-5-blueprint",
                        "modelName": "gpt-5-chat",
                        "providerName": "OpenAI",
                    }
                ]
            },
            "isDefaultChatModel": False,
            "providerConfig": {
                "apiKey": "mock-key",
                "clientId": "mock-client-id",
                "maxAgentLimit": 1000,
            },
        },
    ]
}

MOCK_PLATFORM_SETTINGS = {
    "mcpGateway": {
        "name": "Mock MCP Gateway",
        "url": "https://mock-mcp-gateway.local",
        "status": "active",
        "description": "Mock MCP Gateway for testing",
        "teamAccessToken": "mock-token-12345",
    },
    "workflowOrchestration": {
        "name": "Mock Orchestrator",
        "endpoint": "https://mock-orchestrator.local",
        "status": "active",
        "description": "Mock workflow orchestration service",
    },
    "observability": {
        "description": "Mock observability configuration",
        "backends": [
            {"name": "Phoenix", "status": "active"},
            {"name": "Arize", "status": "active"},
        ],
        "overallStatus": "Healthy",
        "endpoint": "https://localhost:4317",
        "token": "mock-obs-token",
    },
}


def _validate_auth_header(authorization: str = Header(None)) -> str:
    """Validate authorization header. Returns token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")
    return authorization.split(" ", 1)[1]


@app.post("/agenticapps/api/v1/apps/")
async def create_app(
    request_body: Dict[str, Any],
    authorization: str = Header(None),
    x_team_id: str = Header(None),
    x_user_id: str = Header(None),
    x_user_email: str = Header(None),
):
    """Mock endpoint for creating an agentic app."""
    _validate_auth_header(authorization)

    if not x_team_id:
        raise HTTPException(status_code=400, detail="X-Team-Id header required")

    app_id = str(uuid4())
    app_data = {
        "agentic_app_name": request_body.get("agentic_app_name"),
        "app_description": request_body.get("app_description"),
        "category": request_body.get("category"),
        "id": app_id,
        "app_id": app_id,
        "team_id": x_team_id,
        "user_id": x_user_id,
        "user_email": x_user_email,
        "app_status": "draft",
        "app_version": "1.0.0",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    _apps_store[app_id] = app_data
    return JSONResponse(app_data, status_code=201)


@app.post("/agenticapps/api/v1/agents/")
async def register_agent(
    json_payload: str = Form(...),
    agent_url: str = Form(...),
    authorization: str = Header(None),
    x_team_id: str = Header(None),
):
    """Mock endpoint for registering an agent via multipart form data."""
    _validate_auth_header(authorization)

    if not x_team_id:
        raise HTTPException(status_code=400, detail="X-Team-Id header required")

    # Parse the JSON payload from form data
    try:
        agent_info = json.loads(json_payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid json_payload format")

    agent_id = str(uuid4())
    agent_data = {
        "app_id": agent_info.get("app_id"),
        "app_name": agent_info.get("app_name"),
        "name": f"Agent {agent_id[:8]}",
        "type": agent_info.get("type", "a2a"),
        "provider": agent_info.get("provider", "a2a"),
        "agent_url": agent_url,
        "status": "Success",
        "status_message": "Agent Registered Successfully",
        "metadata": {
            "agent_registry_id": agent_id,
        },
    }

    _agents_store[agent_id] = agent_data
    return JSONResponse(agent_data, status_code=201)


@app.get("/agenticapps/api/v1/configuration/provider-team-configs")
async def get_provider_configurations(
    provider: str = None,
    authorization: str = Header(None),
    x_team_id: str = Header(None),
):
    """Mock endpoint for getting provider configurations."""
    _validate_auth_header(authorization)

    configs = MOCK_PROVIDER_CONFIGS["providers"]

    if provider:
        configs = [c for c in configs if c["provider"].lower() == provider.lower()]

    return JSONResponse(configs, status_code=200)


@app.get("/agenticapps/api/v1/configuration/provider-team-configs/providers/{team_id}")
async def get_provider_settings(
    team_id: str,
    authorization: str = Header(None),
):
    """Mock endpoint for getting provider settings with frameworks and models."""
    _validate_auth_header(authorization)

    return JSONResponse(MOCK_PROVIDER_CONFIGS, status_code=200)


@app.get("/agenticapps/api/v1/platform-settings")
async def get_platform_settings(
    authorization: str = Header(None),
    x_team_id: str = Header(None),
):
    """Mock endpoint for getting platform settings."""
    _validate_auth_header(authorization)

    return JSONResponse(MOCK_PLATFORM_SETTINGS, status_code=200)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse(
        {
            "status": "healthy",
            "service": "Mock ICA Agentic Apps API",
            "apps_count": len(_apps_store),
            "agents_count": len(_agents_store),
        },
        status_code=200,
    )


if __name__ == "__main__":
    port = int(os.getenv("ICA_MOCK_PORT", 8888))
    print(f"Starting Mock ICA Agentic Apps API on http://localhost:{port}")
    print(f"Health check: http://localhost:{port}/health")
    uvicorn.run(app, host="0.0.0.0", port=port)
