from collections.abc import Callable
from typing import Any

from agentstudio_sdk import LLM  # type: ignore[import-untyped]

from .logger import get_logger

logger = get_logger(__name__)


def build_adapters(
    agent_config: dict[str, Any],
    llm_factory: Callable[..., LLM] = LLM,
) -> dict[str, LLM]:
    adapters: dict[str, LLM] = {}

    for agent_name, agent_cfg in agent_config.items():
        if not isinstance(agent_cfg, dict):
            logger.warning("Skipping agent '%s': configuration must be a dict", agent_name)
            continue

        provider = agent_cfg.get("provider")
        model = agent_cfg.get("model")
        if not provider or not model:
            raise RuntimeError(
                f"agent '{agent_name}' configuration must include non-empty 'provider' and 'model'"
            )

        adapters[agent_name] = llm_factory(provider=provider, model=model)

    return adapters
