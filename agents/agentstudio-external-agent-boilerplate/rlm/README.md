# RLM Agent Boilerplate

## Introduction

This is a boilerplate project for building agents with [RLM (Recursive Language Models)](https://github.com/alexzhang13/rlm/blob/main/README.md) integrated with [ICA](https://www.ibm.com/consulting/advantage) via the [A2A protocol](https://a2a-protocol.org/latest/).

### What is RLM?

RLM (Recursive Language Models) is a technique that enables LLMs to process inputs that exceed their context window by outputing code to process the large input in a programatic way. It is called recoursive, because the LLM is given possibility to call itself in the genreated code. Most common pattern that emerges is that LLM genrates code that splits the input in chunks, then calls itself on each chunk with self-genrated prompt.
See the original blog for more: https://alexzhang13.github.io/blog/2025/rlm/.

### Demo

The demo agent answers questions about **Clarissa**, the 1748 epistolary novel by Samuel Richardson — one of the longest works in the English language free of copyrigt. At nearly 900,000 words (over 1 million tokens). This exceeds the context window of most current models, making it an ideal showcase for RLM's recursive compression capabilities.

Example questions you can ask the agent:
- "Who is Clarissa's best friend?"
- "What are the most pivotal moments in the book?"
- "Summarize the book in one page"

**Prerequisites:**

- Python 3.13+
- Make
- `uv` — used for dependency management
- Docker or Podman (for local Phoenix observability)

## Useful commands for local development

```bash
# Install dependencies
make install

# Run dev server
make dev

# Run dev server with automatic local keycloak and phoenix setup
make dev-local

# Run production server
make serve
```

## Running tests

```bash
# Run all API tests (starts the server automatically if not running)
make api-test

# Run all API tests against a running server
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/ -v --tb=short

# Run a single test
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/test_agent_response.py::TestHelloResponse::test_hello_stream_completes_without_errors -v -s

# Run Phoenix logging tests (requires agent running with ICA_OBSERVABILITY=true)
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/test_phoenix_logging.py -v -s

# Run Keycloak authorization tests (requires local Keycloak running via `make ensure-local-keycloak`)
API_TEST_BASE_URL=http://localhost:8000 uv run pytest api-tests/test_auth.py -v -s
```

### Frontend E2E tests (Playwright)

The RLM boilerplate works with the default frontend in `../frontend`.
Run helllo world test:
```bash
cd ../frontend
npm install
npm run test:e2e -- e2e/send-hello.spec.ts
```


## Quick manual health checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/.well-known/agent-card.json

# Send "Hello"
curl -s -X POST http://localhost:8000/v1/rpc \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":1,"params":{"message":{"messageId":"msg-1","role":"user","parts":[{"text":"hello"}]}}}'

# Send "Hello" with keycload authorization
ACCESS_TOKEN=$(curl -s -X POST http://localhost:8180/realms/local-dev/protocol/openid-connect/token \
  -d "grant_type=password" -d "client_id=local-client" -d "username=testuser" -d "password=testuser" | jq -r '.access_token')
curl -s -X POST http://localhost:8000/v1/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":1,"params":{"message":{"messageId":"msg-1","role":"user","parts":[{"text":"hello"}]}}}'

# Send "Hello" with static bearer token
curl -s -X POST http://localhost:8000/v1/rpc \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer local-test-token" \
  -d '{"jsonrpc":"2.0","method":"message/send","id":1,"params":{"message":{"messageId":"msg-1","role":"user","parts":[{"text":"hello"}]}}}'

```

## Configuration

Environment variables are set in a `.env` file. Copy `.env.example` to `.env` and fill in the values.

```bash
cp .env.example .env
```

### Key variables

| Variable | Description |
|---|---|
| `ICA_ENDPOINT` | Base URL for the ICA API |
| `ICA_TOKEN` | Authentication token from ICA agentic apps studio settings |
| `ICA_TEAM_ID` | Your ICA team ID |
| `ICA_APP_ID` | Your ICA app ID |
| `ICA_USER_ID` | Your ICA user ID |
| `ICA_REGISTER_AGENT` | Auto-register agent on startup (`true`/`false`) |
| `ICA_OBSERVABILITY` | Enable Phoenix/OpenTelemetry tracing (`true`/`false`) |
| `PHOENIX_COLLECTOR_ENDPOINT` | Phoenix OTLP endpoint (e.g. `http://localhost:4317/v1/traces`) |
| `PUBLIC_AGENT_URL` | Public URL for agent registration (required when `ICA_REGISTER_AGENT=true`) |
| `KEYCLOAK_ISSUER_URL` | Keycloak issuer URL for JWT authorization (optional) |
| `KEYCLOAK_JWKS_URL` | Keycloak JWKS endpoint for token verification (optional) |
| `KEYCLOAK_USERINFO_URL` | Keycloak userinfo endpoint (optional) |

### Local configuration

Local configuration uses a local Phoenix container for observability and a local Keycloak container for authorization. `ICA_REGISTER_AGENT` is `false`, `ICA_OBSERVABILITY` is `true`. The ICA endpoint and credentials are still required to load models.

`make dev` automatically starts local Phoenix and Keycloak containers if they are not already running. Keycloak is set up with a test realm (`local-dev`), client (`local-client`), and test user (`testuser` / `testuser`).

### DEV configuration

DEV configuration uses a remote Phoenix instance and remote Keycloak. `ICA_REGISTER_AGENT` is `true`, `ICA_OBSERVABILITY` is `true`. Before starting, make sure ngrok is running:

```bash
ngrok http 8000
```

Set `PUBLIC_AGENT_URL` to the ngrok URL in your `.env.dev` file, then run:

```bash
make dev
```

### ICA Integration

See the `agentstudio-sdk` README for full details on the environment variables and ICA integration setup.

## Hooks

This boilerplate supports runtime hooks for `session_start`, `input`, `output`,
`error`, `tool_call`, `tool_result`, and `tool_error`.

To enable the included example handlers:

```bash
export AGENTSTUDIO_HOOKS=hooks_example
```

The sample module lives in [hooks_example.py](/Users/kuba/Documents/Projects/Code/agentstudio-external-agent-boilerplate/rlm/hooks_example.py).

The standard RLM flow remains unchanged. To exercise tool hooks locally, use
the demo commands below:

```bash
/demo-tool context-summary
/demo-tool error simulated failure
```
