import json
from typing import cast

from agentstudio_sdk.hooks import use_hook_context  # type: ignore[import-untyped]
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState
from ..logger import get_logger

logger = get_logger(__name__)


class BookingAgent(BaseAgentWithMCP):
    async def init_tools(self) -> None:
        """Initialize tools but filter out book_flight_remote"""
        tools = await self.mcp_server.get_tools_schema()
        # Filter out book_flight_remote tool
        self.tools = [
            t for t in (tools or [])
            if t.get("toolSpec", {}).get("name") != "book_flight_remote"
        ]
        self.tool_info = [
            {
                "name": t["toolSpec"]["name"],
                "description": t["toolSpec"]["description"],
            }
            for t in self.tools
        ]
        logger.info(f"BookingAgent loaded {len(self.tools)} tools (filtered out book_flight_remote)")

    async def handle_message(self, state: AgentState) -> AgentState:
        with use_hook_context(agent_name="BookingAgent"):
            logger.info("BookingAgent handling message")
            prompt = """You are BookingAgent, a helpful assistant for booking interplanetary flights with Galaxium Travels.

CRITICAL: You MUST complete the booking in ONE TURN. Do NOT repeat tool calls.

BOOKING WORKFLOW - Execute ALL steps in sequence:
1. FIRST: Call 'get_user_id' with name and email (if user doesn't exist, call 'register_user')
2. SECOND: Call 'list_flights' to see available flights
3. THIRD: Identify the correct flight_id matching origin and destination
4. FINAL: Call 'book_flight' with user_id, name, flight_id, and infant_count

IMPORTANT RULES:
- Call each tool ONLY ONCE per booking request
- After getting user_id and flight list, IMMEDIATELY call 'book_flight'
- DO NOT call 'get_user_id' or 'list_flights' multiple times
- NEVER call 'book_flight_remote' - it will fail!

Available tools:
- get_user_id(name, email) → returns user_id
- register_user(name, email) → creates new user
- list_flights() → returns all flights
- book_flight(user_id, name, flight_id, infant_count) → creates booking ✓ USE THIS
- get_bookings(user_id) → retrieves bookings
- cancel_booking(booking_id) → cancels booking
- get_discount_by_booking(booking_id) → gets discount info

Example booking flow:
User: "Book flight for Alice (alice@example.com) from Earth to Mars with 2 infants"
1. get_user_id(name="Alice", email="alice@example.com") → user_id=1
2. list_flights() → find flight_id=1 (Earth→Mars)
3. book_flight(user_id=1, name="Alice", flight_id=1, infant_count=2) → booking created!

Always provide booking confirmation with booking_id, flight details, and total cost."""

            messages = self.build_model_messages(state, prompt)
            try:
                # Loop to allow multiple tool calls in sequence
                max_iterations = 10  # Prevent infinite loops
                iteration = 0
                resp_raw = None
                
                while iteration < max_iterations:
                    iteration += 1
                    resp_raw = await self.generate(messages)

                    tool_requests = self.extract_tool_requests(resp_raw)
                    logger.info(f"Booking tools found (iteration {iteration}): {tool_requests}")

                    if not tool_requests:
                        # No more tools to call, we're done
                        break

                    # Call all requested tools
                    tool_results_content = []
                    for request in tool_requests:
                        logger.info(f"Calling booking tool: {request['name']}...")

                        result = await self.call_mcp({"name": request["name"], "arguments": request["input"]})
                        result_dict = cast(dict, result)

                        if not result_dict or "content" not in result_dict:
                            logger.warning("Empty or error response from booking tool %s", request["name"])
                            tool_results_content.append(
                                {
                                    "toolResult": {
                                        "toolUseId": request["toolUseId"],
                                        "content": [{"text": "The booking tool returned no data. Please try again or check your request."}],
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

                    # Add tool results to messages and continue the loop
                    prompt_update = (
                        "Tool results: "
                        + json.dumps(tool_results_content)
                        + ". Continue with the next step if needed, or provide a final response to the user."
                    )
                    messages = self.build_followup_messages(state, prompt_update)

                # Final response generation
                if resp_raw is None:
                    resp = "I apologize, but I couldn't process your request. Please try again."
                else:
                    resp = self.decode_model_response(resp_raw)

            except Exception:
                logger.error("Error in BookingAgent handle_message", exc_info=True)
                resp = "I apologize, but I encountered an error while processing your booking request. Please try again or contact support."

        state["response"] = resp
        return state

# Made with Bob
