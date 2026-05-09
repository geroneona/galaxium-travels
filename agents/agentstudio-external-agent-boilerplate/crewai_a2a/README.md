# Crewai A2A Boilerplate

## Prerequisites

- Python >=3.13 < 3.14
- uv
- AWS Bedrock models. AWS credentials available in ~/.aws
  Tested with logging in via `aws configure` according to https://docs.aws.amazon.com/cli/latest/userguide/cli-authentication-user.html
- copy `.env.example` to `.env` and adjust the defaults if needed

## Install

Guide: https://docs.crewai.com/en/installation

TLDR:

```bash
uv tool install crewai
crewai install
```

## Run

```bash
uv run a2a

# run with different .env configuration
ENV_FILE=.env.prod uv run a2a
```

## Test

Test single input from terminal

```bash
uv run run_crew "What is the weather going to be tomorrow?"
```

Get agent card: `curl http://localhost:8000/.well-known/agent-card.json`

Send a message to the agent:

```bash
curl -s -X POST http://localhost:8000/v1/rpc  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"jsonrpc": "2.0","method": "message/send","id": 1,"params":
    {"message": {"messageId": "msg-1", "role": "user","parts": [{"text": "hello"}]}}
  }'

```

Test with CLI:

```bash
cd cli-client
uv run . --agent http://localhost:8000
```

GUI for testing the A2A server: https://github.com/a2aproject/a2a-inspector

## The boilerplate flow

The boilerplate contains specialized weather and food agents and an orchestration flow that uses a direct LLM call to classify and route the user's prompt.
Files:

- `main.py` - contains entrypoints for starting the a2a server and testing
- `a2a_server.py` - the a2a server
- `agent_executor.py` - adapter between the A2A server and CrewAI
- `flow.py` - the example flow makes call to LLM to classify the topic, routes to the right specialist agent
- `agents.py` - contains agent definitions

## Implementing Custom Agents, Flow and Crews

- Add or remove agents:
  1. add or remove agents in `agents.py` according to existing agent examples.
  2. add or remove agents steps in `flow.py` and their topics in the classification LLM call.

CrewAI allows to execute a singla Agent, a Flow, or a Crew with a `.kickoff` method. The `.kickoff` is called in `agent_executor.py`.
For developing the agent beyond the example Flow-Agent structure refer to CrewAI docuemntation https://docs.crewai.com/en/introduction.

### Rulebook AI MCP Server Configuration

The term reader and term writer agents require connection to a Rulebook AI MCP server for term management operations.

- `RULEBOOK_MCP_SERVER_URL`: **Required** for term agents - This is the Base URL of the shared MCP Gateway (you can find it in the Platform Settings). Format: `https://<MCP_GATEWAY_BASE_URL>/servers/<server-id>/mcp`
  - **Where to get it**: Log in to [IBM Enterprise Advantage Platform](https://servicesessentials.ibm.com/agenticapps), navigate to the Platform Settings (see screenshot below.)

- `RULEBOOK_BEARER_TOKEN`: **Required** for term agents. Authentication token for the Rulebook AI MCP server.
  - **Where to get it**: In the Agent Studio, go to Platform Settings and copy the MCP Gateway Access Token. **Important**: Only provide the token value without the "Bearer " prefix (it's added automatically by the code).
  - Example: `RULEBOOK_BEARER_TOKEN="your-token-here"` (not `RULEBOOK_BEARER_TOKEN="Bearer your-token-here"`)

**Note**: If these variables are not set, the term reader and term writer agents will be skipped during startup, and the system will continue with other available agents.

![Platform Settings - Enterprise Advantage](img/platform_settings.png)

## Optional bearer token (A2A auth)

This A2A server supports an optional single-token bearer authentication for messaging endpoints. Configure the token in your environment (for example, in `.env`):

- `A2A_BEARER_TOKEN`: when set, the server will require incoming requests to include an `Authorization: Bearer <token>` header for protected endpoints.

Behavior:

- If `A2A_BEARER_TOKEN` is not set, authentication is disabled and requests are accepted (convenient for local development).
- When `A2A_BEARER_TOKEN` is set, the middleware validates the bearer token for message endpoints; the agent-card endpoint (`/.well-known/agent-card.json`) is left public and excluded from auth checks so clients can discover the agent card.

Example to set the token:

```bash
export A2A_BEARER_TOKEN=supersecret
```

## Hooks

This boilerplate supports runtime hooks for `session_start`, `input`, `output`,
`error`, `tool_call`, `tool_result`, and `tool_error`.

To enable the included example handlers:

```bash
export AGENTSTUDIO_HOOKS=hooks_example
```

The sample module lives in [hooks_example.py](hooks_example.py).
CrewAI MCP tools emit tool hooks through the custom MCP tool wrapper in
`mcp_tools_handler.py`.
