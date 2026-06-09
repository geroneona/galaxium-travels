import os

from dotenv import load_dotenv

load_dotenv()

from functools import cached_property
from agentstudio_sdk import ICASettings  # type: ignore[import-untyped]


class Settings:
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

    @property
    def ICA_MODEL(self):
        return os.getenv("ICA_MODEL", "amazon.nova")

    @cached_property
    def ica(self):
        ica_settings = ICASettings.from_env(agent_url=self.PUBLIC_AGENT_URL)
        return ica_settings

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
