import os

from dotenv import load_dotenv
from functools import cached_property
from agentstudio_sdk import ICASettings  # type: ignore[import-untyped]

load_dotenv()


class Settings:
    AWS_REGION = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "eu-central-1"
    AWS_PROFILE = os.getenv("AWS_PROFILE")

    _DEFAULT_ALLOWED_ORIGINS = ",".join(
        (
            "http://localhost:5173",
            "http://localhost:4173",
            "http://localhost:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:4173",
            "http://127.0.0.1:3000",
        )
    )

    @property
    def ALLOWED_ORIGINS(self):
        return [
            o.strip() for o in os.environ.get("ALLOWED_ORIGINS", self._DEFAULT_ALLOWED_ORIGINS).split(",") if o.strip()
        ]

    PORT = int(os.getenv("PORT", 8000))

    @property
    def PUBLIC_AGENT_URL(self):
        return os.environ.get("PUBLIC_AGENT_URL", f"http://localhost:{self.PORT}/")

    @cached_property
    def ica(self):
        """Get ICA settings initialized from environment variables.

        Returns an ICASettings instance populated from ICA_* environment
        variables, with agent_url set to PUBLIC_AGENT_URL.

        Returns:
            ICASettings instance
        """
        ica_settings = ICASettings.from_env(agent_url=self.PUBLIC_AGENT_URL)
        return ica_settings

    # Weather Agent
    WA_MCP_SERVER_URL = os.getenv("WA_MCP_SERVER_URL")
    WA_AUTHORIZATION = os.getenv("WA_AUTHORIZATION", "")

    # Rulebook AI MCP Server
    RULEBOOK_MCP_SERVER_URL = os.getenv("RULEBOOK_MCP_SERVER_URL")
    RULEBOOK_BEARER_TOKEN = os.getenv("RULEBOOK_BEARER_TOKEN", "")

    A2A_PROTOCOL = os.getenv("A2A_PROTOCOL", "JSONRPC")
    SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", 30 * 60))
    SESSION_MAX_MESSAGES = int(os.getenv("SESSION_MAX_MESSAGES", 20))

    @property
    def agent_endpoint_path(self):
        if self.A2A_PROTOCOL != "JSONRPC":
            return ""

        rpc_path = os.getenv("RPC_PATH") or "/v1/rpc"
        if not rpc_path.startswith("/"):
            rpc_path = f"/{rpc_path}"
        return rpc_path

    @property
    def agent_endpoint_url(self):
        return self.PUBLIC_AGENT_URL.rstrip("/") + self.agent_endpoint_path


settings = Settings()
