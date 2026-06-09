from typing import Any, Optional, List

from a2a.types import AgentCard as BaseAgentCard


class ExtendedAgentCard(BaseAgentCard):
    """Shared ExtendedAgentCard used by multiple backends.

    Keeps compatibility with the upstream `AgentCard` model while exposing
    `supportedInterfaces` (camelCase) and ensuring serialized output uses
    camelCase keys required by the A2A spec.
    """

    supported_interfaces: Optional[List[Any]] = None

    def dict(self, *args: Any, **kwargs: Any) -> dict:
        # Prefer pydantic v2 `model_dump(by_alias=True)` to ensure camelCase
        # serialization. Fall back to `dict(..., by_alias=True)` for older
        # pydantic versions.
        try:
            base = super().model_dump(by_alias=True, **(kwargs or {}))
        except Exception:
            base = super().dict(*args, **{**(kwargs or {}), "by_alias": True})

        if self.supported_interfaces is not None:
            base["supportedInterfaces"] = self.supported_interfaces
            base.pop("supported_interfaces", None)

        pref = getattr(self, "preferred_transport", None)
        if pref is not None:
            base["preferredTransport"] = pref
        base.pop("preferred_transport", None)

        return base
