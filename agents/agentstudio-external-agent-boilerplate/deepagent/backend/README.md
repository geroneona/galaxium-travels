# Agentic Chat Backend with DeepAgent

## Introduction
This is a boilerplate project that can be used to quickly get started with developing agents built with LangChain's [DeepAgent SDK](https://docs.langchain.com/oss/python/deepagents/overview) integrated with [ICA](https://www.ibm.com/consulting/advantage) via [A2A protocol](https://a2a-protocol.org/latest/)

The integration includes:
 * Automatic agent registration for use in agentic apps studio workflows
 * Use of ICA models
 * Observability


### Deep agents
Deep agent is a concept popularized by [LangChain's blog](https://blog.langchain.com/deep-agents/). Deep agent is an agent harness, a framework with built-in capabilities for managing agents, that enable solving more complex long-running tasks.

Main features:
* **Sub-agents** Intelligent delegation of tasks to specialized agents.
Have specialized instructions, help avoid context bloat.
* **Planning** built-in TODO list tool supports breaking down the problem and plan the steps to solution.
* **Fine tuned system prompt** 
* **Memory & File system tools** store important information through long sessions and acroos multiple sessions.

The example agent is a recruitment asistant who can support with analyzing CVs and comparing against job descriptions. Its purpose is to be a small example easy to set up, to there are no tools involved to minimize dependencies.
The example agent consists of 4 sub-agents defined by their prompts:
* CV parser
* Job description analyzer
* Skill gap analyzer
* Culture fit evaluator
See `src/agent.py` for more details.

**Prerequisites:**

- Python 3.13+
- Make
- A virtual environment (recommended)
- `uv` (recommended) — used to install and run dependency-group dev tools from `pyproject.toml`

## Useful commands for local development

```bash
# Install dependencies
make install
# run dev srever
make dev
# run API tests
make api-tests
# run single API test
uv run pytest api-tests/test_sse_streaming.py::TestSSEStreamingHappyPath::test_stream_delivers_working_then_completed -v -s


# Quick manual health checks
curl http://localhost:8000/health
curl http://localhost:8000/.well-known/agent-card.json

# Send "Hello"
curl -s -X POST http://localhost:8000/v1/rpc  -H "Content-Type: application/json" -d '
  {"jsonrpc": "2.0","method": "message/send","id": 1,"params":
    {"message": {"messageId": "msg-1", "role": "user","parts": [{"text": "hello"}]}}
  }'

# Send "Hello" with authorization
curl -s -X POST http://localhost:8000/v1/rpc  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"jsonrpc": "2.0","method": "message/send","id": 1,"params":
    {"message": {"messageId": "msg-1", "role": "user","parts": [{"text": "hello"}]}}
  }'
```

## Configuration
Environment variables can be set with `.env` file. See `.env.example` for list of variables that can be set.


### ICA Integration (Agentic Chat Backend)
- See the configuration described in `agentstudio-sdk` README (section **Environment Variables**).

## Hooks

This boilerplate supports runtime hooks for `session_start`, `input`, `output`,
`error`, `tool_call`, `tool_result`, and `tool_error`.

To enable the included example handlers:

```bash
export AGENTSTUDIO_HOOKS=hooks_example
```

The sample module lives in [hooks_example.py](/Users/kuba/Documents/Projects/Code/agentstudio-external-agent-boilerplate/deepagent/backend/hooks_example.py).
DeepAgent emits tool hooks from its streamed activity updates, including the
delegation/task tool used during deep-agent execution.
