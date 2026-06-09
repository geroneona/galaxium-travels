import asyncio
from typing import Any

from agentstudio_sdk.llm import LLM
from openinference.instrumentation import using_metadata
from langgraph.graph import StateGraph
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class BaseAgent:
    mcp = False

    def __init__(self, model: LLM, graph: StateGraph):
        self.model = model
        # keep attribute name `orchestrator` for compatibility with older code
        self.orchestrator = graph
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _run_init(self) -> None:
        await self.model.init()

    async def init(self) -> None:
        if self._initialized:
            return
        async with self._init_lock:
            if self._initialized:
                return
            await self._run_init()
            self._initialized = True

    async def generate(self, prompt: str | list[dict[str, Any]], tools: list | None = None) -> Any:
        await self.init()
        with using_metadata({"agent_name": self.__class__.__name__}):
            return await self.model.generate(prompt, tools)

    def build_model_messages(
        self,
        state: AgentState,
        instruction: str,
    ) -> list[dict[str, str]]:
        messages = self._conversation_messages(state)
        if not messages:
            messages = [{"role": "user", "content": state.get("utterance", "")}]

        for index in range(len(messages) - 1, -1, -1):
            if messages[index]["role"] == "user":
                messages[index] = {
                    "role": "user",
                    "content": f"{instruction}\n\nCurrent user request: {messages[index]['content']}",
                }
                return messages

        return [{"role": "user", "content": instruction}, *messages]

    def build_followup_messages(
        self,
        state: AgentState,
        prompt: str,
    ) -> list[dict[str, str]]:
        messages = self._conversation_messages(state)
        messages.append({"role": "user", "content": prompt})
        return messages

    def _conversation_messages(self, state: AgentState) -> list[dict[str, str]]:
        raw_messages = state.get("messages") or []
        messages: list[dict[str, str]] = []
        for message in raw_messages:
            role = message.get("role")
            content = message.get("content", "")
            if role not in {"user", "assistant"}:
                continue
            messages.append({"role": role, "content": str(content)})
        return messages

    async def handle_message(self, state: AgentState) -> object:
        raise NotImplementedError()

    def decode_model_response(self, resp: Any) -> str:
        """Decode model response from either Azure OpenAI or Bedrock format."""
        try:
            # If it's already a string, return it
            if isinstance(resp, str):
                return resp

            # Try Azure OpenAI format (ChatCompletion object)
            if hasattr(resp, "choices") and len(resp.choices) > 0:
                choice = resp.choices[0]
                if hasattr(choice, "message") and hasattr(choice.message, "content"):
                    content = choice.message.content
                    if isinstance(content, str):
                        return content

            # Try Bedrock format (dict with nested structure)
            if isinstance(resp, dict):
                # Bedrock format: output.message.content[0].text
                try:
                    return resp["output"]["message"]["content"][0]["text"]
                except (KeyError, IndexError, TypeError):
                    pass

                # Alternative: try direct content access
                try:
                    if "content" in resp:
                        return resp["content"]
                except (KeyError, TypeError):
                    pass

            # Fallback: try to convert to string
            return str(resp)
        except Exception as e:
            logger.error(f"Failed to decode model response: {e}, response type: {type(resp)}")
            return ""
