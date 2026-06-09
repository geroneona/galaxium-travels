import json
from typing import cast

from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class TermWriterAgent(BaseAgentWithMCP):
    """
    TermWriterAgent creates new terms in Rulebook AI.
    Uses MCP server to call POST Terms tool.
    Supports both Azure OpenAI and Bedrock response formats.
    Handles parameter collection and validation.
    """

    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="TermWriterAgent"):
            logger.info("TermWriterAgent handling message")

            prompt = """You are TermWriterAgent, a specialized agent for creating new terms in Rulebook AI.

Your task is to:
1. Collect all necessary information to create a term (name, definition, category, etc.)
2. Validate that required parameters are provided
3. Use the available tools to create the term
4. Confirm successful creation or ask for missing information

If the user hasn't provided all required information, ask clarifying questions.
Respond professionally and guide the user through the term creation process."""
            messages = self.build_model_messages(state, prompt)

            try:
                resp_raw = await self.generate(messages)

                tool_requests = self.extract_tool_requests(resp_raw)

                logger.info(f"TermWriterAgent found {len(tool_requests)} tool requests")

                if tool_requests:
                    tool_results_content = []
                    for request in tool_requests:
                        tool_name = request.get("name", "")
                        tool_input = request.get("input", {})
                        logger.info(f"TermWriterAgent calling {tool_name} tool with input: {tool_input}")

                        # Validate required parameters before calling MCP
                        if not tool_input:
                            logger.warning(f"No input parameters provided for {tool_name}")
                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request.get("toolUseId", ""),
                                        "content": [
                                            {
                                                "text": "Missing required parameters for term creation. Please provide term name, definition, and other relevant details."
                                            }
                                        ],
                                    }
                                }
                            )
                            continue

                        try:
                            result = await self.call_mcp({"name": tool_name, "arguments": tool_input})
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
                                                    "text": "Term creation failed. The server returned an empty response. Please verify your input and try again."
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
                            error_message = str(e)

                            # Provide user-friendly error messages
                            if "validation" in error_message.lower():
                                user_message = f"Validation error: {error_message}. Please check that all required fields are provided correctly."
                            elif "duplicate" in error_message.lower():
                                user_message = "A term with this name already exists. Please choose a different name."
                            elif "permission" in error_message.lower() or "unauthorized" in error_message.lower():
                                user_message = (
                                    "You don't have permission to create terms. Please contact your administrator."
                                )
                            else:
                                user_message = f"Error creating term: {error_message}. Please try again or contact support if the issue persists."

                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request.get("toolUseId", ""),
                                        "content": [{"text": user_message}],
                                    }
                                }
                            )

                    # Generate final response with tool results
                    prompt_update = (
                        "This is the updated response with tool results: "
                        + json.dumps(tool_results_content)
                        + ". Generate a clear, user-friendly response based on the term creation results. "
                        + "If successful, confirm what was created. If there were errors, explain them clearly. "
                        + "Do not explicitly mention the JSON response or technical details."
                    )
                    resp_raw = await self.generate(self.build_followup_messages(state, prompt_update), [])

                resp = self.decode_model_response(resp_raw)

            except Exception:
                logger.error("Error in TermWriterAgent handle_message", exc_info=True)
                resp = (
                    "I encountered an error while trying to create the term. "
                    "Please ensure you've provided all required information (term name, definition, etc.) "
                    "and try again. Contact support if the issue persists."
                )

        state["response"] = resp
        return state


# Made with Bob
