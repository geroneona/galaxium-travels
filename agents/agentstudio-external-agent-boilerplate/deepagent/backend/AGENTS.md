# Agents in DeepAgents

This document describes how to implement, configure, and manage agents in the DeepAgents framework.

## Overview

The DeepAgents project is a boilerplate backend for an agentic chat application that orchestrates agents and exposes them via the A2A protocol. The framework provides a simple API for building custom agents that handle different types of user requests.

## Architecture

- **Agent Framework**: DeepAgents (v0.4.7+)
- **Protocol**: A2A (JSON-RPC or HTTP+JSON)
- **Key Components**:
  - Supervisor Agent: Routes user utterances to appropriate agents
  - Individual Agents: Handle specific types of requests
  - MCP Server Support: Optional integration with Model Context Protocol servers
  - State Management: AgentState object carries context between steps

## Docs
`docs` folder contains more documentation files. Scan the folder and read the files that seem related to your current task.
Pay special attention to the `.docs/PRD.md` file. It contains the product requirements. When user requests new functionality, check the PRD doc for conflicts.
Always write down new requested requirements in PRD doc.

### External docs
- [A2A Protocol](https://a2a-protocol.org/latest/)
- [DeepAgents Github](https://github.com/deepagent/deepagents)
- [DeepAgents Docs pages - quickstart](https://docs.langchain.com/oss/python/deepagents/quickstart)


## Testing

Run the server for development: `make dev`.

Run API tests with: `make api-test`. The API level tests need the server to be running.
The tests are in the `./api-tests` folder.
API level tests are prefered over unit tests fro the main product requirements.


## General rules of conduct
* do not create extra docs, scripts, summary or report files unless explicitly asked to.
* when you get the same error after 3 attempts to fix it, then stop and respond with a summary of what is the error, how to reproduce it and briefly describe the failed fix attempts.
