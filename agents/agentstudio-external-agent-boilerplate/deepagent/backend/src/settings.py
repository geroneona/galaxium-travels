import os

from dotenv import load_dotenv

# Load .env BEFORE importing agentstudio_sdk so that environment variables (e.g.
# ICA_TOKEN) are available when agentstudio_sdk initialises its module-level singletons.
load_dotenv()

from functools import cached_property
from agentstudio_sdk import ICASettings  # type: ignore[import-untyped]


class Settings:
    AWS_REGION = (
        os.getenv("AWS_REGION")
        or os.getenv("AWS_DEFAULT_REGION")
        or "eu-central-1"
    )
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
            o.strip()
            for o in os.environ.get(
                "ALLOWED_ORIGINS", self._DEFAULT_ALLOWED_ORIGINS
            ).split(",")
            if o.strip()
        ]

    PORT = int(os.getenv("PORT", 8000))

    @property
    def PUBLIC_AGENT_URL(self):
        return os.environ.get(
            "PUBLIC_AGENT_URL", f"http://localhost:{self.PORT}/"
        )

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

    WA_MCP_SERVER_URL = os.getenv("WA_MCP_SERVER_URL")
    WA_AUTHORIZATION = os.getenv("WA_AUTHORIZATION", "")

    @cached_property
    def a2a_protocol(self):
        protocol = os.getenv("A2A_PROTOCOL", "JSONRPC")
        valid_protocols = {"JSONRPC", "HTTP+JSON"}
        if protocol not in valid_protocols:
            raise ValueError(
                f"A2A_PROTOCOL must be one of {valid_protocols}, "
                f"got '{protocol}'"
            )
        return protocol

    @property
    def agent_endpoint_path(self):
        if self.a2a_protocol != "JSONRPC":
            return ""

        rpc_path = os.getenv("RPC_PATH") or "/v1/rpc"
        if not rpc_path.startswith("/"):
            rpc_path = f"/{rpc_path}"
        return rpc_path

    @property
    def agent_endpoint_url(self):
        return self.PUBLIC_AGENT_URL.rstrip("/") + self.agent_endpoint_path


settings = Settings()
