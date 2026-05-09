---
name: implement-custom-agent
description: Implements a new custom agent in the agentstudio-external-agent-boilerplate backend. Use this skill when adding a new agent class under backend/src/agents/, registering it in the exports and config, or replacing an existing agent. Covers both standard agents (BaseAgent) and MCP-enabled agents (BaseAgentWithMCP).
---

# Implement Custom Agent

## When to use
- Adding a new agent that handles a specific user intent (e.g. a new domain, tool, or workflow)
- Replacing or extending an existing agent in `backend/src/agents/`
- Wiring a new agent into the supervisor routing and config

## When NOT to use
- Editing the supervisor routing logic itself → edit [`backend/src/agents/supervisor.py`](backend/src/agents/supervisor.py) directly
- Changing model/provider defaults across all agents → edit [`backend/src/config/agents.py`](backend/src/config/agents.py) directly
- Adding LangGraph nodes or graph topology → that belongs in `backend/src/langgraph_integration.py`

## Inputs required
- Agent name (lowercase, hyphen-separated for config key; `PascalCase` for class name)
- Whether the agent needs MCP tool access (`BaseAgentWithMCP`) or not (`BaseAgent`)
- Model provider + alias to use (see existing entries in [`backend/src/config/agents.py`](backend/src/config/agents.py) for reference)
- (MCP only) `mcp_server_url` and `auth_key` values

---

## Workflow

### Step 1 — Create the agent module

Create `backend/src/agents/<my_agent>.py`. Choose the correct base class:

**Standard agent** (no MCP tools):
```python
# backend/src/agents/my_agent.py
from .base import BaseAgent
from ..state import AgentState

class MyAgent(BaseAgent):
    async def handle_message(self, state: AgentState) -> AgentState:
        utterance = state.get('utterance', '')
        prompt = f"You are MyAgent. User asked: {utterance}\nRespond concisely."
        resp_raw = await self.generate(prompt)
        state['response'] = self.decode_model_response(resp_raw)
        return state
```

**MCP-enabled agent** (needs tool calls):
```python
# backend/src/agents/my_agent_mcp.py
import json
from .base_with_mcp import BaseAgentWithMCP
from ..state import AgentState

class MyAgentMCP(BaseAgentWithMCP):
    async def handle_message(self, state: AgentState) -> AgentState:
        utterance = state.get('utterance', '')
        prompt = f"You are MyAgentMCP. User asked: {utterance}\nRespond concisely."
        resp_raw = await self.generate(prompt)          # tool-enabled pass
        tool_requests = self.extract_tool_requests(resp_raw)
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
            resp_raw = await self.generate(
                f"Tool results: {json.dumps(tool_results_content)}. "
                "Generate a response based on this insight.", []
            )
        state['response'] = self.decode_model_response(resp_raw)
        return state
```

Key API facts:
- [`self.generate(prompt)`](backend/src/agents/base.py:34) — awaitable; calls the configured LLM; pass `tools=[]` for a no-tools follow-up
- [`self.decode_model_response(resp)`](backend/src/agents/base.py:41) — handles both Azure OpenAI and Bedrock response envelopes; always use this instead of accessing response fields directly
- [`state`](backend/src/state.py) — mapping-like [`AgentState`](backend/src/state.py); standard keys: `utterance`, `contextId`, `response`

### Step 2 — Export the agent

Add your class to [`backend/src/agents/__init__.py`](backend/src/agents/__init__.py):

```python
from .my_agent import MyAgent   # add this line

__all__ = [
    ...,
    "MyAgent",
]
```

### Step 3 — Register in config

Add an entry to the `AGENTS` dict in [`backend/src/config/agents.py`](backend/src/config/agents.py). The dict key becomes the agent's routing ID used by the supervisor.

```python
"my-agent": {
    "provider": PREFERRED_PROVIDER or "azure",
    "model": PREFERRED_MODEL or "gpt-4o",
    "name": "My Agent",
    "description": "Short description used by the supervisor to route requests",
    # MCP-only fields (omit if not using MCP):
    # "mcp_server_url": settings.MY_MCP_SERVER_URL,
    # "auth_key": settings.MY_AUTH_KEY,
},
```

> The `description` field is injected into the supervisor's classification prompt — write it so the supervisor can accurately route user utterances to this agent.

### Step 4 — Write a test

Add a focused test in [`backend/tests/test_app.py`](backend/tests/test_app.py) (or [`backend/tests/test_agents_async.py`](backend/tests/test_agents_async.py) for async unit tests). Mock `self.model.generate` to return a fixture response and assert `state['response']` is set correctly.

### Step 5 — Verify routing

Run the backend locally and send a message that should route to your new agent. Check that:
1. The supervisor selects your agent's key (log output or test assertion)
2. `handle_message` returns a populated `state['response']`

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Supervisor never routes to new agent | `description` in `config/agents.py` is too vague | Rewrite with concrete trigger phrases |
| `decode_model_response` returns `""` | Unexpected response envelope | Log `resp_raw` type and structure; check provider config |
| MCP tools not discovered | `mcp_server_url` missing or wrong | Confirm the key in `config/agents.py` and `settings` |
| `NotImplementedError` at runtime | Forgot to override `handle_message` | Implement the method in your subclass |
