import json
from typing import cast

from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class WeatherAgent(BaseAgentWithMCP):
    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="WeatherAgent"):
            logger.info("WeatherAgent handling message")
            prompt = "You are WeatherAgent. Respond concisely with weather-related information or questions."
            messages = self.build_model_messages(state, prompt)
            try:
                resp_raw = await self.generate(messages)

                tool_requests = self.extract_tool_requests(resp_raw)
                logger.info(f"Tools which have been found: {tool_requests}")

                if tool_requests:
                    tool_results_content = []
                    for request in tool_requests:
                        logger.info(f"Calling {request['name']} tool...")

                        result = await self.call_mcp({"name": request["name"], "arguments": request["input"]})
                        result_dict = cast(dict, result)

                        if not result_dict or "content" not in result_dict:
                            logger.warning("Empty or error response from MCP tool %s", request["name"])
                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request["toolUseId"],
                                        "content": [{"text": "The weather tool returned no data. Please try again."}],
                                    }
                                }
                            )
                            continue

                        tool_results_content.append(
                            {
                                "toolResult": {
                                    "toolUseId": request["toolUseId"],
                                    "content": [{"text": str(result_dict["content"][0]["text"])}],
                                }
                            }
                        )

                    prompt_update = (
                        "This is the updated response with tool results: "
                        + json.dumps(tool_results_content)
                        + ". Generate some response based on this insight but do not explicitly mention the JSON response."
                    )
                    resp_raw = await self.generate(self.build_followup_messages(state, prompt_update), [])

                resp = self.decode_model_response(resp_raw)

            except Exception:
                logger.error("Error in WeatherAgent handle_message", exc_info=True)
                resp = ""

        state["response"] = resp
        return state
