"""
Class that defines the API for agentic apps to interact with the ICA.
"""

import os
import httpx
import json
from typing import Optional, Any, Dict, List, TypedDict, NotRequired
from enum import Enum
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv
from .auth import Authenticator

_env_paths = [
    Path.cwd() / ".env",
    Path(__file__).parent.parent.parent.parent / "backend" / ".env",
]

for _env_path in _env_paths:
    if _env_path.exists():
        load_dotenv(_env_path)
        break

if os.environ.get("ENV_FILE"):
    load_dotenv(dotenv_path=os.environ.get("ENV_FILE"), override=True)


class Provider(Enum):
    aws = "aws"
    azure = "azure"

@dataclass
class CreateAppRequest:
    """Request payload for creating an agentic app."""

    agentic_app_name: str
    app_description: str
    category: str
    business_objective: Optional[str] = None


@dataclass
class RegisterAgentRequest:
    """Request payload for registering an A2A agent."""

    user_id: str
    app_name: str
    app_id: str
    type: str  # e.g., "a2a"
    provider: str  # e.g., "a2a"
    agent_url: str


# TypedDict definitions for platform settings response
class MCPGateway(TypedDict):
    """MCP Gateway configuration."""

    name: str
    url: str
    status: str
    description: str
    teamAccessToken: str


class WorkflowOrchestration(TypedDict):
    """Workflow orchestration service configuration."""

    name: str
    endpoint: str
    status: str
    description: str


class ObservabilityBackend(TypedDict):
    """Individual observability backend status."""

    name: str
    status: str


class Observability(TypedDict):
    """Observability configuration including monitoring backends."""

    description: str
    backends: List[ObservabilityBackend]
    overallStatus: str
    endpoint: str
    token: str


class PlatformSettings(TypedDict):
    """Root structure for platform settings response."""

    mcpGateway: MCPGateway
    workflowOrchestration: WorkflowOrchestration
    observability: Observability


class MCPServerDetails(TypedDict):
    """MCP server connection details returned by get_mcp_server."""

    url: str
    access_token: str


# TypedDict definitions for provider settings and configurations
class ChatModel(TypedDict):
    """Model configuration for chat operations."""

    modelId: str
    modelName: str
    description: NotRequired[str]
    providerName: NotRequired[str]
    inputModalities: NotRequired[List[str]]
    outputModalities: NotRequired[List[str]]
    customizationsSupported: NotRequired[List[str]]
    inferenceTypesSupported: NotRequired[List[str]]
    capabilities: NotRequired[List[str]]
    config: NotRequired[Dict[str, Any]]


class ModelConfig(TypedDict):
    """Configuration for available models."""

    models: List[ChatModel]
    defaultMaxTokens: NotRequired[int]
    defaultTemperature: NotRequired[float]


class ProviderInstance(TypedDict):
    """Provider instance details."""

    id: int
    name: str
    createdAt: str
    updatedAt: str
    deletedAt: NotRequired[Optional[str]]


class ProviderConfigSettings(TypedDict):
    """Provider-specific configuration settings."""

    region: NotRequired[str]
    accountId: NotRequired[str]
    accessKeyId: NotRequired[str]
    secretAccessKey: NotRequired[str]
    maxAgentLimit: NotRequired[int]
    lambdaEndpointUrl: NotRequired[str]
    apiKey: NotRequired[str]
    clientId: NotRequired[str]
    tenantId: NotRequired[str]
    apiBaseUrl: NotRequired[str]
    apiVersion: NotRequired[str]
    endpointUrl: NotRequired[str]
    clientSecret: NotRequired[str]
    applicationInsightsConnection: NotRequired[str]
    azureOpenAiApiKey: NotRequired[str]
    azureOpenAiEndpoint: NotRequired[str]
    azureOpenAiApiVersion: NotRequired[str]
    projectEndpointUrl: NotRequired[str]
    modelEndpoint: NotRequired[str]
    azureOpenAiResourceName: NotRequired[str]


class ProviderTeamConfig(TypedDict):
    """Provider configuration for a team."""

    teamId: str
    providerId: int
    chatModelConfig: ModelConfig
    frameworkIds: List[int]
    isDefaultChatModel: bool
    providerConfig: ProviderConfigSettings
    modelConfig: ModelConfig
    isActive: bool
    createdAt: str
    updatedAt: str
    deletedAt: NotRequired[Optional[str]]
    provider: NotRequired[ProviderInstance]


class ProviderSettings(TypedDict):
    """Provider settings with details about frameworks and models."""

    provider: str
    provider_id: int
    frameworks: List[str]
    models: List[ChatModel]
    chatModelConfig: ModelConfig
    isDefaultChatModel: bool
    providerConfig: ProviderConfigSettings


class ProvidersResponse(TypedDict):
    """Root response structure for provider settings."""

    providers: List[ProviderSettings]


class ModelCredentials(TypedDict):
    """AWS model credentials returned by get_model_credentials."""
    modelId: str
    accessKeyId: str
    secretAccessKey: str
    region: str


class AgenticAppsAPI:
    """
    Client for interacting with ICA Agentic Apps API.

    Handles authentication and provides methods for managing agentic apps,
    registering agents, and retrieving configurations.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_token: str = "",
        team_id: str = "",
        user_id: str = "",
        user_email: str = "",
    ):
        """
        Initialize the AgenticAppsAPI client.

        Args:
            base_url: Base URL for the ICA Agentic Apps API. If not provided,
                     reads from ICA_ENDPOINT environment variable,
                     defaults to https://dev-us.servicesessentials.ibm.com/agenticapps/api/v1
            api_token: JWT or API token for authentication
            team_id: Team ID for API requests
            user_id: User ID for API requests
            user_email: User email for API requests
        """
        self.base_url = base_url or os.getenv(
            "ICA_ENDPOINT",
            "https://dev-us.servicesessentials.ibm.com/agenticapps/api/v1",
        )
        self.api_token = os.getenv("ICA_TOKEN", api_token)
        self.team_id = os.getenv("ICA_TEAM_ID", team_id)
        self.user_id = os.getenv("ICA_USER_ID", user_id)
        self.user_email = os.getenv("ICA_USER_EMAIL", user_email)
        self._platform_settings_cache: Optional[PlatformSettings] = None

    def _get_headers(self) -> Dict[str, str]:
        """Get common request headers."""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "X-Team-Id": self.team_id,
        }
        if self.user_id:
            headers["X-User-Id"] = self.user_id
        if self.user_email:
            headers["X-User-Email"] = self.user_email
        print(f"@@ headers: {headers}")
        return headers

    async def create_app(
        self,
        request: CreateAppRequest,
    ) -> Dict[str, Any]:
        """
        Create a new agentic app.

        Args:
            request: CreateAppRequest with app details

        Returns:
            Response containing app details including app_id
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/apps/",
                headers=self._get_headers(),
                json={
                    "agentic_app_name": request.agentic_app_name,
                    "app_description": request.app_description,
                    "category": request.category,
                    "business_objective": request.business_objective,
                },
            )
            response.raise_for_status()
            return response.json()

    async def register_agent(
        self,
        app_id: str,
        agent_url: str,
        app_name: Optional[str] = None,
        agent_type: str = "a2a",
        provider: str = "a2a",
    ) -> Dict[str, Any]:
        """
        Register an A2A agent.

        Args:
            app_id: ID of the agentic app
            app_name: Name of the agentic app
            agent_url: URL of the agent
            agent_type: Type of agent (default: "a2a")
            provider: Provider type (default: "a2a")

        Returns:
            Response containing agent registration status and metadata
        """
        json_payload = {
            "app_id": app_id,
            "type": agent_type,
            "provider": provider,
        }
        if self.user_id:
            json_payload["user_id"] = self.user_id
        if app_name:
            json_payload["app_name"] = app_name
        
        # Check if authentication is enabled for the agent
        # Currently this registers the token maintained in `A2A_BEARER_TOKEN` env variable
        # as we do not have enough environment details available to generate keycloak token for registration
        # Therefore we have additional check to validate the `A2A_BEARER_TOKEN` value is not None
        authenticator_obj = Authenticator()
        authentication_enabled = authenticator_obj.is_enabled()
        agent_bearer_token = authenticator_obj._bearer_token
        if not authentication_enabled or not agent_bearer_token:
            raise ValueError("Agent registration is enabled (ICA_REGISTER_AGENT=true) but A2A_BEARER_TOKEN is not set."
                + "It is required for agent registration and subsequent authentication of messages coming from ICA workflow.")
        agent_auth_type = 'bearer_token'    # keeping this `bearer` as we currently support this auth mechanism only
        agent_credentials = {'token': agent_bearer_token}

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/agents/",
                headers={
                    "Authorization": f"Bearer {self.api_token}",
                    "X-Team-Id": self.team_id,
                },
                files={
                    "json_payload": (None, json.dumps(json_payload)),
                    "agent_url": (None, agent_url),
                    "auth_type": (None, agent_auth_type),
                    "credentials": (None, json.dumps(agent_credentials))
                },
            )
            response.raise_for_status()
            return response.json()

    async def get_provider_configurations(
        self,
        provider: Optional[str] = None,
    ) -> List[ProviderTeamConfig]:
        """
        Get provider configurations for the team.

        Args:
            provider: Optional filter by provider name (e.g., "AWS", "Azure")

        Returns:
            List of provider configurations
        """
        async with httpx.AsyncClient(timeout=60.0) as client:
            params = {"team_id": self.team_id}
            if provider:
                params["provider"] = provider

            response = await client.get(
                f"{self.base_url}/configuration/provider-team-configs",
                headers={"Authorization": f"Bearer {self.api_token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()

    def get_provider_configurations_sync(
        self,
        provider: Optional[str] = None,
    ) -> List[ProviderTeamConfig]:
        """
        Synchronous variant of get_provider_configurations.

        Suitable for module-level or non-async initialization code.

        Args:
            provider: Optional filter by provider name (e.g., "AWS", "Azure")

        Returns:
            List of provider configurations
        """
        with httpx.Client() as client:
            params = {"team_id": self.team_id}
            if provider:
                params["provider"] = provider

            response = client.get(
                f"{self.base_url}/configuration/provider-team-configs",
                headers={"Authorization": f"Bearer {self.api_token}"},
                params=params,
            )
            response.raise_for_status()
            return response.json()

    async def get_provider_settings(
        self,
        team_id: Optional[str] = None,
    ) -> ProvidersResponse:
        """
        Get provider settings including providers, frameworks, and models.

        Args:
            team_id: Team ID (uses instance team_id if not provided)

        Returns:
            Provider settings with available providers and frameworks
        """
        team = team_id or self.team_id
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/configuration/provider-team-configs/providers/{team}",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            return response.json()

    async def get_platform_settings(
        self, use_cache: bool = True
    ) -> PlatformSettings:
        """
        Get platform settings including MCP gateway and orchestration details.

        Args:
            use_cache: When True (default), returns a cached result if available
                       and skips the network call.

        Returns:
            Platform settings with service endpoints and configurations
        """
        if use_cache and self._platform_settings_cache is not None:
            return self._platform_settings_cache

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(
                f"{self.base_url}/platform-settings",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            self._platform_settings_cache = response.json()
            return self._platform_settings_cache

    def get_platform_settings_sync(
        self, use_cache: bool = True
    ) -> PlatformSettings:
        """
        Synchronous variant of get_platform_settings.

        Suitable for module-level or non-async initialization code.

        Args:
            use_cache: When True (default), returns a cached result if available
                       and skips the network call.

        Returns:
            Platform settings with service endpoints and configurations
        """
        if use_cache and self._platform_settings_cache is not None:
            return self._platform_settings_cache

        with httpx.Client() as client:
            response = client.get(
                f"{self.base_url}/platform-settings",
                headers=self._get_headers(),
            )
            response.raise_for_status()
            self._platform_settings_cache = response.json()
            return self._platform_settings_cache

    def get_mcp_server_sync(self, server_id: str) -> MCPServerDetails:
        platform_settings = self.get_platform_settings_sync()
        mcp_gateway = platform_settings.get("mcpGateway", {})
        gateway_url = mcp_gateway["url"].rstrip("/")
        url = f"{gateway_url}/servers/{server_id}/mcp"
        access_token = mcp_gateway["teamAccessToken"]
        return MCPServerDetails(url=url, access_token=access_token)
    
    def get_model_credentials(self, model_name: str) -> ModelCredentials:
        """Utilify function to find specified model credentials from ICA platform"""

        # Get provider configurations using sync method
        configs = self.get_provider_configurations_sync(
            provider=Provider.aws.value
        )

        if not configs:
            raise ValueError("No AWS provider configuration found in ICA platform")

        config = configs[0]
        provider_config = config.get("providerConfig", {})

        model_config = config.get("modelConfig", {})
        model_id = next(
            (
                m.get("modelId")
                for m in model_config.get("models", [])
                if model_name in (m.get("modelId") or "")
            ),
            None,
        )

        if not model_id:
            raise ValueError(f"No {model_name} model found in model configuration")

        credentials = {
            "modelId": model_id,
            "accessKeyId": provider_config.get("accessKeyId"),
            "secretAccessKey": provider_config.get("secretAccessKey"),
            "region": provider_config.get("region", "us-east-1"),
        }

        if not credentials["accessKeyId"] or not credentials["secretAccessKey"]:
            raise ValueError(
                "AWS credentials not properly configured in ICA platform"
            )

        return credentials



agentic_apps_api = AgenticAppsAPI()
