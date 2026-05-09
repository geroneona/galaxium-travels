"""agentstudio_sdk package exports.

Expose commonly-used submodules at package level for convenience, e.g.

```py
from agentstudio_sdk import phoenix, auth
app.add_middleware(auth.AuthenticatorMiddleware)
```
"""

from . import (
    phoenix,
    hooks,
    mcp_server_adapter,
    mcp_circuit_breaker,
    logger,
    auth,
    agent_registration,
    settings,
)
from .extended_agent_card import ExtendedAgentCard
from .agent_registration import register_agent_when_ready
from .settings import ICASettings
from .llm import LLM
from .initialization import initialize_ica
from .mcp_circuit_breaker import MCPServerWithCircuitBreaker

__all__ = [
    "phoenix",
    "hooks",
    "mcp_server_adapter",
    "mcp_circuit_breaker",
    "logger",
    "auth",
    "agent_registration",
    "register_agent_when_ready",
    "settings",
    "ICASettings",
    "ExtendedAgentCard",
    "LLM",
    "MCPServerWithCircuitBreaker"
]
