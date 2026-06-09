import json
from typing import cast

from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class TermReaderAgent(BaseAgentWithMCP):
    """
    TermReaderAgent retrieves and searches terms from Rulebook AI.
    Uses MCP server to call GET Terms tool.
    Supports both Azure OpenAI and Bedrock response formats.
    """

    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="TermReaderAgent"):
            logger.info("TermReaderAgent handling message")

            prompt = """You are TermReaderAgent, a specialized agent for retrieving terms from Rulebook AI.

Your task is to:
1. Identify what term information the user is looking for
2. Use the available tools to retrieve the relevant terms
3. Present the information in a clear, concise manner

        Respond with the term information or ask clarifying questions if needed."""
            messages = self.build_model_messages(state, prompt)

            try:
                resp_raw = await self.generate(messages)

                tool_requests = self.extract_tool_requests(resp_raw)

                logger.info(f"TermReaderAgent found {len(tool_requests)} tool requests")

                if tool_requests:
                    tool_results_content = []
                    for request in tool_requests:
                        tool_name = request.get("name", "")
                        logger.info(f"TermReaderAgent calling {tool_name} tool...")

                        try:
                            result = await self.call_mcp(
                                {
                                    "name": tool_name,
                                    "arguments": request.get("input", {}),
                                }
                            )
                            result_dict = cast(dict, result)

                            # Handle empty or invalid MCP responses
                            if not result_dict or "content" not in result_dict:
                                logger.warning(f"Empty or invalid response from MCP tool {tool_name}")
                                tool_results_content.append(
                                    {
                                        "toolResult": {
                                            "toolUseId": request.get("toolUseId", ""),
                                            "content": [
                                                {
                                                    "text": "No results found. The term database may be empty or the query returned no matches."
                                                }
                                            ],
                                        }
                                    }
                                )
                                continue

                            # Extract text from MCP response
                            content_text = str(result_dict["content"][0].get("text", ""))

                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request.get("toolUseId", ""),
                                        "content": [{"text": content_text}],
                                    }
                                }
                            )

                        except Exception as e:
                            logger.error(
                                f"Error calling MCP tool {tool_name}: {e}",
                                exc_info=True,
                            )
                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request.get("toolUseId", ""),
                                        "content": [
                                            {
                                                "text": f"Error retrieving terms: {str(e)}. Please try again or contact support if the issue persists."
                                            }
                                        ],
                                    }
                                }
                            )

                    # Generate final response with tool results
                    prompt_update = (
                        "This is the updated response with tool results: "
                        + json.dumps(tool_results_content)
                        + ". Generate a clear, user-friendly response based on the term information retrieved. "
                        + "Format the terms nicely and explain what was found. "
                        + "Do not explicitly mention the JSON response or technical details."
                    )
                    resp_raw = await self.generate(self.build_followup_messages(state, prompt_update), [])

                resp = self.decode_model_response(resp_raw)

            except Exception:
                logger.error("Error in TermReaderAgent handle_message", exc_info=True)
                resp = (
                    "I encountered an error while trying to retrieve term information. "
                    "Please try rephrasing your question or contact support if the issue persists."
                )

        state["response"] = resp
        return state


# Made with Bob
