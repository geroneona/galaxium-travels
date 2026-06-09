from typing import Any
from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from config.agents import AGENTS as CONFIG_AGENTS
from langgraph.graph import StateGraph
from ..state import AgentState
from ..logger import get_logger
from .base import BaseAgent

logger = get_logger(__name__)


class SupervisorAgent(BaseAgent):
    def __init__(
        self,
        model: Any,
        graph: StateGraph,
        agents_registry: dict | None = None,
    ):
        super().__init__(model, graph)
        self.agents_registry = agents_registry or {}

    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="SupervisorAgent"):
            if state.get("target", None) == "supervisor":
                logger.info("SupervisorAgent: fallback")
                state["response"] = "I'm sorry, I couldn't determine the best agent to assist you."
                return state

            available_agents = [name for name in self.agents_registry.keys() if name != "supervisor"]
            if not available_agents:
                logger.warning("SupervisorAgent: no downstream agents available")
                state["response"] = "I'm sorry, no specialist agents are currently available."
                return state

            prompt = self._build_prompt(available_agents, state)
            messages = self.build_model_messages(state, prompt)

            classification_raw = await self.generate(messages)
            classification = self._decode_classification(classification_raw)

            logger.info(f"SupervisorAgent: classified to '{classification}'")

            if classification in self.agents_registry:
                logger.info(f"Supervisor routing to agent '{classification}'")
                state["target"] = classification
            else:
                logger.info("Supervisor routing back to supervisor")
                state["target"] = "supervisor"
            return state

    def _build_prompt(self, available_agents: list[str], state: AgentState) -> str:
        lines = [
            "You are an intent classifier. Given the user's message,",
            "choose the single best agent to handle it from the list below.",
            "Reply with the agent id only.",
        ]
        lines.append("Available agents:")
        for name in available_agents:
            cfg = CONFIG_AGENTS.get(name, {})
            desc = cfg.get("description", "") if isinstance(cfg, dict) else ""
            lines.append(f"- {name}: {desc}")

        return "\n".join(lines)

    def _decode_classification(self, raw) -> str:
        out = self.decode_model_response(raw).lower().strip()
        if out:
            return out

        # Fallback: attempt to decode ChatCompletion-like object
        try:
            choices = getattr(raw, "choices", None)
            if not choices:
                return ""
            first = choices[0]
            msg = getattr(first, "message", None)
            if msg is None:
                return ""
            content = getattr(msg, "content", None)
            if isinstance(content, str) and content:
                out = content.lower().strip()
            elif hasattr(content, "content"):
                inner = getattr(content, "content")
                if isinstance(inner, str) and inner:
                    out = inner.lower().strip()
        except Exception:
            out = ""
        return out
