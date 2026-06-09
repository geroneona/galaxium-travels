# Multi-Agent System with Rulebook AI Integration

This document describes the multi-agent system architecture and the implemented agents, including Rulebook AI term management capabilities.

## Architecture Overview

The system uses a hierarchical agent orchestration pattern with a Supervisor agent that routes user requests to specialized worker agents:

```
┌─────────────────┐
│   Supervisor    │ ← Entry point, routes requests
│    (Manager)    │
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼──┐  ┌──▼────┐ ┌─▼──────┐ ┌─▼──────┐
│Weather│ │ Meal  │ │Term    │ │Term    │
│Agent  │ │Agent  │ │Reader  │ │Writer  │
└───────┘ └───────┘ └────────┘ └────────┘
                        │          │
                        └────┬─────┘
                             │
                        ┌────▼────┐
                        │   MCP   │
                        │ Server  │
                        └─────────┘
```

## Implemented Agents

### 1. Supervisor Agent

**Purpose**: Routes user requests to the appropriate specialized agent based on intent classification.

**Behavior**:

- Analyzes user utterances to determine intent
- Dynamically discovers available agents from the registry
- Routes requests to the most appropriate worker agent
- Returns responses from worker agents to the user

**Implementation**: `src/agents/supervisor.py`

**No manual routing updates needed** - the supervisor automatically includes all agents registered in `src/config/agents.py` by reading their descriptions.

---

### 2. Weather Agent

**Purpose**: Provides weather information and forecasts.

**Capabilities**:

- Current weather conditions
- Weather forecasts
- Temperature information
- Location-based weather queries

**MCP Integration**: Uses weather MCP server for real-time data

**Configuration**:

```bash
WA_MCP_SERVER_URL=<weather-mcp-server-url>
WA_AUTHORIZATION=<auth-token>
```

**Implementation**: `src/agents/weather.py` (subclass of `BaseAgentWithMCP`)

---

### 3. Meal Agent

**Purpose**: Provides meal suggestions, recipes, and food-related assistance.

**Capabilities**:

- Recipe recommendations
- Meal planning suggestions
- Cooking tips
- Dietary information

**Implementation**: `src/agents/meal.py` (subclass of `BaseAgent`)

---

### 4. Term Reader Agent (Rulebook AI)

**Purpose**: Retrieves and searches for terms from the Rulebook AI knowledge base.

**Capabilities**:

- Search for terms by name or description
- Retrieve term definitions
- List available terms
- Query term metadata

**MCP Integration**: Uses Rulebook AI MCP server with GET Terms tool

**Routing Triggers**: User queries containing:

- "see", "get", "list", "view", "show", "find", "search" + "term(s)"
- "what is", "define", "explain" + term-related keywords

**Configuration**:

```bash
RULEBOOK_MCP_SERVER_URL=https://agentstudio.servicesessentials.ibm.com/servers/<server-id>/mcp
RULEBOOK_BEARER_TOKEN="<your-token>"
```

**Important**: Only provide the token value in `RULEBOOK_BEARER_TOKEN`. The "Bearer " prefix is added automatically by the code.

**Implementation**: `src/agents/term_reader.py` (subclass of `BaseAgentWithMCP`)

**Key Features**:

- Dual format response parsing (supports both Bedrock and Azure OpenAI)
- Empty response detection and user-friendly error messages
- Automatic MCP tool discovery on initialization
- Graceful error handling with detailed logging

---

### 5. Term Writer Agent (Rulebook AI)

**Purpose**: Creates new terms in the Rulebook AI knowledge base.

**Capabilities**:

- Create new term definitions
- Validate term parameters
- Handle duplicate term detection
- Provide creation confirmation

**MCP Integration**: Uses Rulebook AI MCP server with POST Terms tool

**Routing Triggers**: User queries containing:

- "create", "add", "post", "write", "new" + "term"
- "define a new", "add a definition"

**Configuration**: Same as Term Reader Agent (shares MCP server)

**Implementation**: `src/agents/term_writer.py` (subclass of `BaseAgentWithMCP`)

**Key Features**:

- Parameter collection and validation
- Dual format response parsing (Bedrock and Azure OpenAI)
- Enhanced error handling (validation, duplicate, permission errors)
- User-friendly error messages with actionable guidance

---

## MCP Server Configuration

### Rulebook AI MCP Server

The Rulebook AI agents require an MCP server connection for term management operations.

**Environment Variables**:

```bash
RULEBOOK_MCP_SERVER_URL=https://agentstudio.servicesessentials.ibm.com/servers/<server-id>/mcp
RULEBOOK_BEARER_TOKEN="<your-token>"
```

**Available Tools**:

- `GET Terms` - Retrieve and search terms (used by Term Reader)
- `POST Terms` - Create new terms (used by Term Writer)

**Authentication**: Bearer token authentication. Only provide the token value; the "Bearer " prefix is added automatically.

**HTTP Method Support**: The MCP adapter automatically falls back from POST to GET if the server returns a 405 Method Not Allowed error.

---

## Implementation Guide

### Adding New Agents

To add a new agent to the system:

1. **Define Agent Configuration** in `src/config/agents.py`:

   ```python
   "agent-name": {
       "description": "Agent description for routing",
       "model_alias": "bedrock_nova_lite",
       # For MCP-enabled agents:
       "mcp_server_url": os.getenv("AGENT_MCP_SERVER_URL"),
       "auth_key": os.getenv("AGENT_AUTHORIZATION")
   }
   ```

2. **Create Agent Implementation** in `src/agents/<agent-name>.py`:
   - For agents without MCP: subclass `BaseAgent`
   - For agents with MCP: subclass `BaseAgentWithMCP`
   - Implement `async def handle_message(self, state: AgentState) -> AgentState`

3. **Add Environment Variables** in `.env`:

   ```bash
   AGENT_MCP_SERVER_URL=<mcp-server-url>
   AGENT_AUTHORIZATION="Bearer <token>"  # Include "Bearer " prefix
   ```

4. **Register Settings** in `src/config/settings.py`:

   ```python
   AGENT_MCP_SERVER_URL = os.getenv("AGENT_MCP_SERVER_URL")
   AGENT_AUTHORIZATION = os.getenv("AGENT_AUTHORIZATION", "")
   ```

5. **Export Agent Class** in `src/agents/__init__.py`:

   ```python
   from .agent_name import AgentNameClass
   ```

6. **Add Initialization Logic** in `src/main.py`:
   - Follow the pattern used for term-reader and term-writer agents
   - Include MCP server setup, tool discovery, and error handling

7. **No Supervisor Changes Needed**: The supervisor automatically discovers and routes to new agents based on their descriptions in `src/config/agents.py`.

### Agent Implementation Patterns

#### BaseAgent Pattern (No MCP)

```python
from .base import BaseAgent
from ..state import AgentState

class MyAgent(BaseAgent):
    async def handle_message(self, state: AgentState) -> AgentState:
        utterance = state.get('utterance', '')
        prompt = f"You are MyAgent. User asked: {utterance}"
        resp_raw = await self.generate(prompt)
        state['response'] = self.decode_model_response(resp_raw)
        return state
```

#### BaseAgentWithMCP Pattern (With MCP Tools)

```python
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState
import json

class MyAgentMCP(BaseAgentWithMCP):
    async def handle_message(self, state: AgentState) -> AgentState:
        utterance = state.get('utterance', '')
        prompt = f"You are MyAgentMCP. User asked: {utterance}"

        # Generate with discovered MCP tools
        resp_raw = await self.generate(prompt)

        # Parse tool requests (dual format support)
        tool_requests = self.extract_tool_requests(resp_raw)

        # Call MCP tools
        if tool_requests:
            tool_results_content = []
            for request in tool_requests:
                result = await self.call_mcp({
                    "name": request['name'],
                    "arguments": request['input']
                })
                tool_results_content.append({
                    "toolResult": {
                        "toolUseId": request['toolUseId'],
                        "content": [{"text": str(result['content'][0]['text'])}]
                    }
                })

            # Generate final response with tool results
            resp_raw = await self.generate(
                f"Tool results: {json.dumps(tool_results_content)}. Generate response.",
                []
            )

        state['response'] = self.decode_model_response(resp_raw)
        return state
```

---

## Testing

### Manual Testing

Test the agents using the CLI client:

```bash
cd cli-client
uv run . --agent http://localhost:8001
```

### Test Queries

**Weather Agent**:

- "What's the weather like today?"
- "Will it rain tomorrow?"

**Meal Agent**:

- "Suggest a healthy dinner recipe"
- "What should I cook tonight?"

**Term Reader Agent**:

- "Show me all terms"
- "What is the definition of [term-name]?"
- "Search for terms about [topic]"

**Term Writer Agent**:

- "Create a new term called [name] with definition [definition]"
- "Add a term for [concept]"

---

## Troubleshooting

### Common Issues

**Agent Not Responding**:

- Check that the agent is registered in `src/config/agents.py`
- Verify environment variables are set correctly
- Check logs for initialization errors

**MCP Tool Failures**:

- Verify MCP server URL is accessible
- Check authorization token format (must include "Bearer " prefix)
- Review MCP server logs for errors
- Ensure MCP tools were discovered during initialization

**Routing Issues**:

- Supervisor automatically routes based on agent descriptions
- Check agent description in `src/config/agents.py` matches user intent
- Review supervisor logs for classification decisions

**Authorization Errors (401)**:

- Verify `RULEBOOK_BEARER_TOKEN` is set correctly (token value only, without "Bearer " prefix)
- Verify token is valid and not expired
- Check token has required permissions

**HTTP Method Errors (405)**:

- MCP adapter automatically falls back from POST to GET
- Check MCP server supports required HTTP methods
- Review adapter logs for fallback behavior

---

## Dependencies

Required packages for MCP integration:

- `httpx>=0.28` - HTTP client for MCP communication
- `requests>=2.31` - Fallback HTTP client
- `urllib3>=2.0` - URL encoding for GET requests

See `pyproject.toml` for complete dependency list.

---

## Additional Resources

- **LangGraph Documentation**: https://docs.crewai.com/en/introduction
- **MCP Protocol Specification**: https://modelcontextprotocol.io/
- **Enterprise Advantage Platform**: https://servicesessentials.ibm.com/agenticapps
- **Agent Implementation Examples**: See `src/agents/` directory

---

## Version History

- **v1.0** - Initial implementation with weather and meal agents
- **v2.0** - Added Rulebook AI integration with term-reader and term-writer agents
  - Added MCP HTTP method fallback support
  - Added Azure OpenAI tool calling support
  - Fixed authorization header format
  - Added dual format response parsing
