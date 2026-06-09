import os
import logging
from typing import List

from crewai import Agent
from crewai.tools import BaseTool
from agentstudio_sdk.llm import LLM, Provider, CrewAILLM
from agentstudio_sdk.agentic_apps_api import agentic_apps_api

# Import custom MCP tools handler
from .mcp_tools_handler import get_mcp_tools

logger = logging.getLogger(__name__)

# Initialize custom LLM with ICA discovery
# CrewAI agents require synchronous LLM interface, so we use generate_sync()
# The flow will handle async initialization; here we just instantiate
# Using Azure provider with fallback to ICA provider
bedrock_llm = CrewAILLM(LLM(provider=Provider.azure, model="gpt-4o"))


def get_mcp_tools_from_weather_server() -> List[BaseTool]:
    """Get MCP tools from the weather MCP server."""
    if os.getenv("WA_MCP_SERVER_URL") is not None:
        return get_mcp_tools(
            os.getenv("WA_MCP_SERVER_URL"),
            auth_headers={"Authorization": f"Bearer {os.getenv('WA_AUTHORIZATION')}"},
        )

    server_id = os.getenv("ICA_MCP_SERVER_ID")
    if server_id is not None:
        mcp_server = agentic_apps_api.get_mcp_server_sync(server_id)
        return get_mcp_tools(
            mcp_server['url'],
            auth_headers={"Authorization": f"Bearer {mcp_server['access_token']}"},
        )

    return []


def get_mcp_tools_from_rulebook_server() -> List[BaseTool]:
    """Get MCP tools from the Rulebook AI MCP server."""
    if os.getenv("RULEBOOK_MCP_SERVER_URL") is not None:
        token = os.getenv("RULEBOOK_BEARER_TOKEN", "")
        return get_mcp_tools(
            os.getenv("RULEBOOK_MCP_SERVER_URL"),
            auth_headers={"Authorization": f"Bearer {token}"} if token else {},
        )

    return []


# Get weather tools from MCP server and pass as custom tools to agent
weather_tools = get_mcp_tools_from_weather_server()
weather_kwargs = {
    "role": "Weather agent",
    "goal": "Respond concisely with weather related information",
    "backstory": "You are weather agent, you give advice about the weather.",
    "verbose": True,
    "llm": bedrock_llm,
}
if weather_tools:
    weather_kwargs["tools"] = weather_tools

weather_agent = Agent(**weather_kwargs)
food_agent = Agent(
    role="Meal agent",
    goal="Respond with meal/food information in a concise way.",
    backstory="You are Meal Agent, you give advice about food.",
    verbose=True,
    llm=bedrock_llm,
)

# Rulebook AI Term Management Agents
rulebook_tools = get_mcp_tools_from_rulebook_server()

term_reader_kwargs = {
    "role": "Term Reader Agent",
    "goal": "Retrieve and display business terms from the Rulebook AI glossary using GET operations only",
    "backstory": """You are a Term Reader Agent specialized in retrieving business term definitions from the Rulebook AI glossary.
    You help users understand business terminology by fetching accurate definitions.
    
    IMPORTANT: You MUST actually call the MCP tools to retrieve data - do not make up or hallucinate responses.
    You should ONLY use GET/read operations to retrieve existing terms.
    When calling MCP tools, use empty parameters {} to retrieve all terms, or provide search criteria if available.
    Never attempt to create or modify terms - that's the Term Writer Agent's job.""",
    "verbose": True,
    "llm": bedrock_llm,
    "allow_delegation": False,
    "max_iter": 10,
}
if rulebook_tools:
    term_reader_kwargs["tools"] = rulebook_tools

term_reader_agent = Agent(**term_reader_kwargs)

term_writer_kwargs = {
    "role": "Term Writer Agent",
    "goal": "Create new business terms in the Rulebook AI glossary",
    "backstory": "You are a Term Writer Agent specialized in creating new business term definitions in the Rulebook AI glossary. You help users document business terminology by creating well-structured term entries.",
    "verbose": True,
    "llm": bedrock_llm,
    "allow_delegation": False,
    "max_iter": 10,
}
if rulebook_tools:
    term_writer_kwargs["tools"] = rulebook_tools

term_writer_agent = Agent(**term_writer_kwargs)
