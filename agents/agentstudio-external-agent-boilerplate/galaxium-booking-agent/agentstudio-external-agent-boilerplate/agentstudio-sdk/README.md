# agentstudio-sdk

Shared SDK for agentstudio boilerplates.

## IBM Consulting Advantage Setup

In order to use this boilerplate with IBM Consulting Advantage, the following steps are recommended:

1. Create a new team (currently it will not work in Workspace). The ID of the created
team has to be stored in env. variable `ICA_TEAM_ID` (in **IBM Consulting Advantage** the team id is visible in the URL when we click on the team name in the top menu).

1. In your team create an Agentic App (left menu, item **Agent & Assitant Studio**, then click on **Create an Agentic App**). We need to store the app id (visible in app detail) in env. variable `ICA_APP_ID`.

1. Generate API key for the team – in **IBM Consluting Advantage** go to the list of your apps, click on the setup button in the top right-hand corner, go to tab **API Keys** and generate a new API key. Store the generated key in env. variable `ICA_TOKEN` (**IMPORTANT**: This is a different key than the one you can generate in global settings of **IBM Consulting Advantage**).

[Visual guide](https://github.ibm.com/Consulting-DTT-AI-Integration-Services/agentstudio-external-agent-boilerplate/wiki/How-to-get-required-ICA_*-env-variables)

## Environment Variables

Apart from `ICA_TEAM_ID`, `ICA_APP_ID` and `ICA_TOKEN` mentioned in the **IBM Consulting Advantage Setup**, the SDK uses the following environment variables:

- `ICA_ENDPOINT`: **Required**. Endopint for **IBM Consulting Advantage** API (**DEV**: [https://dev-us.servicesessentials.ibm.com/agenticapps/api/v1], **PROD**: [https://servicesessentials.ibm.com/agenticapps/api/v1]). Defaults to the dev endpoint.
- `ICA_APP_NAME`: **Required** for agent registration.
- `ICA_USER_ID`: Optional. Recommended. When set, the auto registered agent belongs to the user, and the user gets right to delete it.
- `ICA_AGENT_TYPE`: Optional. Type of agent. Defaults to `a2a`.
- `ICA_PROVIDER`: Optional. Provider identifier. Defaults to `a2a`.
- `ICA_REGISTER_AGENT`: Optional. Enable/disable automatic agent registration (true/false). Defaults to `false`. Accepts: `true`, `false`, `1` or anything else including empty string means registration is disabled.
- `ICA_OBSERVABILITY`: Optional. Whether observability data should be sent to Phoenix (defaults to `false`).

- `PHOENIX_COLLECTOR_ENDPOINT`: Optional. Phoenix collector endpoint for observability (e.g., `http://localhost:6006/v1/traces`). Overrides endpoint loaded from ICA API when set.
- `PHOENIX_API_KEY`: Optional. Only wokrs if PHOENIX_COLLECTOR_ENDPOINT is set.

## Local Development

The SDK should be automatically linked to the backends of individual
boilerplates in a development mode – this should be ensured by running `make
install` on the backend. Also the `make dev` command should reload the
application in case of any change in the SDK source.

## SDK Capabilities

### Runtime Hooks

The SDK can load optional runtime hook modules from the `AGENTSTUDIO_HOOKS`
environment variable.

- Format: comma-separated Python module paths
- Supported events:
  - `session_start`
  - `session_end`
  - `input`
  - `output`
  - `error`
  - `tool_call`
  - `tool_result`
  - `tool_error`
- Hook modules can expose either:
  - `register_agentstudio_hooks(registry)`
  - `HOOKS = {"event_name": handler}`

All boilerplates in this repository now include a `hooks_example.py` module, so
the simplest local setup is:

```bash
AGENTSTUDIO_HOOKS=hooks_example
```

Hook failures are isolated: the SDK logs them and continues processing the
agent request.

### Observability with Phoenix

Phoenix consumes the Open Telemetry data emitted by the backend and provides
observability features.

To use it in your code you have add `PhoenixSessionMiddleware` as a middleware
to your A2A application:

```
from a2a.server.apps.rest import A2ARESTFastAPIApplication
from agentstudio_sdk.phoenix import PhoenixSessionMiddleware

app = A2ARESTFastAPIApplication(...).build()
app.add_middleware(PhoenixSessionMiddleware)
```

and then log user utterance and agent response in the following way:

```
from agentstudio_sdk.phoenix import create_agent_span, set_agent_output

with create_agent_span(SESSION_ID, UTTERANCE) as agent_span:
    # compute AGENT_RESPONSE from AI
    set_agent_output(agent_span, RESPONSE)
```

If you want to check Phoenix logs locally, run Phoenix in Podman:

```
podman run -p 6006:6006 -p 4317:4317 -i -t arizephoenix/phoenix:latest
```

set the local endpoint in your backend `.env` file:

```
ICA_OBSERVABILITY=true
PHOENIX_COLLECTOR_ENDPOINT='http://localhost:4317'
```

and open `http://localhost:6006` in your browser to see the Phoenix dashboard.

### Agent Registration

The SDK can automatically register your agent in IBM Consulting Advantage on application startup.

**How it works**: on initialization the SDK starts a background thread that polls your agent's well-known agent card endpoint (the SDK polls `http://localhost:<port>/.well-known/agent-card.json`) until it becomes reachable. Once the card endpoint is accessible the SDK calls the ICA Agentic Apps API to register the agent. This only happens if the `ICA_REGISTER_AGENT` environment variable is set to `true`.

Here is a code fragment demonstrating how to use it in your agent:

```
from agentstudio_sdk.initialization import initialize_ica

...
# Agent registration to ICA is included in the following call
initialize_ica(AGENT_CONFIGURATION, PORT) 
``` 

Check also [Environment Variables](#environment-variables) to see what configuration is relevant to this functionality.
Agent registration requires also [authentication](#authentication) with `A2A_BEARER_TOKEN` enabled.
The value of `A2A_BEARER_TOKEN` will be passed to ICA during agent registration, so that the calls from Agent Studio workflows can authenticate.

## Authentication

The SDK includes a small bearer-token authenticator that backends can
optionally enable. Set the following environment variable in your
backend's `.env` file to enable token-based authentication for the
JSONRPC messaging endpoint (`/v1/rpc`):

```
A2A_BEARER_TOKEN=...
```

When `A2A_BEARER_TOKEN` is set, incoming requests to the messaging API must include the header `Authorization: Bearer <token>`.
If the env var is not set, authentication is disabled for local development convenience.


## ICA LLM Agents

The SDK provides API to connect to LLMs exposed by ICA. To use this feature
initilize the models at application startup in this way:

```
from agentstudio_sdk import LLM

llm = LLM(provider = "aws", model="claude-sonnet")
await llm.init()
```

This code will fetch the LLMs exposed by ICA and will use the enpoint matching
the `provider` and `model` parameters. For `model` a substring match is applied.
The ICA API for LLM endpoints is called just once – the response is cached in
the application memory. If ICA does not expose a matching endpoint, the `init()`
call raises an exception.

The `llm` is then used as follows from async application code:

```
response = await llm.generate(prompt)
```

For CrewAI the SDK offers a subclass of CrewAI's BaseLLM that can be used like
this:

**Note**: If unsure what LLMs are exposed by ICA, check the application logs –
the `LLM.init()` method logs all the models that were found.

```
from crewai import Agent
from agentstudio_sdk.llm import LLM, CrewAILLM

llm = LLM(provider=Provider.aws, model="claude-sonnet")
await llm.init()
crewai_llm = CrewAILLM(llm)

agent = Agent(
    role="...",
    goal="...",
    backstory="...",
    llm=crewai_llm
)
```
