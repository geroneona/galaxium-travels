from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from .base import BaseAgent
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class MealAgent(BaseAgent):
    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="MealAgent"):
            logger.info("MealAgent handling message")
            prompt = "You are MealAgent. Respond with meal/food information."
            messages = self.build_model_messages(state, prompt)
            try:
                resp_raw = await self.generate(messages)
                resp = self.decode_model_response(resp_raw)
            except Exception:
                resp = ""
        state["response"] = resp
        return state
