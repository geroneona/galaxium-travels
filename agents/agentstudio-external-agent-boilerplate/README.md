# Enterprise Advantage External Agent Boilerplate

> [!Tip]
> If you have any questions that the README below does not answer, please contact us on this Slack channel - [#ica-procode-agents](https://ibm.enterprise.slack.com/archives/C0AMS5PANMA)

This repository contains reference implementations for building AI agents using agent orchestration frameworks such as LangGraph and CrewAI, while retaining the benefits of the IBM Enterprise Advantage platform.

## Purpose

In the Enterprise Advantage platform, you can build agents using the Agentic App Studio in a no-code experience. This allows you to quickly spin up AI agents, which are integrated with the platform's LLM Gateway and Observability by default.

The purpose of this repository is to show you how to build custom AI agents in a pro-code experience.

This will allow you to build agents using standard agent orchestration frameworks, as well as to build more complex applications that require a combination of deterministic code and agentic behavior.

### Common Use Cases

You should consider using this repository, if your client:

- **Wants to build agents outside of the Enterprise Advantage Agentic App Studio**, but wants to keep the observability and governance benefits of the platform.
- **Has existing agents built and deployed already**, but wants to integrate them with the Enterprise Advantage platform, in order to:
  - **Centralize the management** of all of their agentic applications under one roof
  - **Integrate with new agents** built using the Enterprise Advantage Agentic App Studio
  - **Use the platform's observability** to track the full lifecycle of your agentic application

### Repository Contents

This template repository contains a list of boilerplate agents, that show you how to build agentic applications that are automatically integrated to the Enterprise Advantage platform.

This integration pattern is enabled by using our SDK (`agentstudio-sdk/`), that allows you to build Agents that register with your Enterprise Advantage application at runtime.

This means that you can build agents in any framework of your choice (such as LangGraph or CrewAI), and these agents will use Enterprise Advantage's LLM Model Gateway, Observability and other governance features.

Furthermore, you will be able to see these agents in the platform's UI and integrate them with other agents you build inside Enterprise Advantage's Agentic App Studio.

### Development Process

> [!Warning]  
> Please note that we **do NOT provide deployment support** for these boilerplate applications.
>
> When you follow the instructions below, the new repository will contain a Dockerfile you can use to deploy on any standard cloud container service.
>
> For non-production workloads, we recommend you create a Docker Compose and run it on a small virtual machine.

The start developing agents using these boilerplate, you need to follow this process:

1. **Initialize the template**: use the scripts below to initialize your new repository with your intended framework (currently LangGraph or CrewAI), deployment type (see below), and other settings the prompt will ask you for.
2. **Develop the agents**: the new repository will contain example implementations of agents in your chosen framework and documentation that explains how to obtain the necessary environment variables to integrate with the platform.
3. **Deploy your application**: The repository is set up with a Dockerfile that produces a standard container image that you can then distribute and deploy using your client's established processes. **We do not provide support with deployment beyond advice on the contents of this repository.**

In summary, a Developer using this repository is able to:

- Easily spin up a repository based on the selected boilerplate template.
- Implement any requested changes (including with the support of code agents like IBM Bob, Claude Code or OpenAI Codex).
- Locally test the implementation with our prepackaged basic chat UI.
- Deploy the solution using pre-packaged Dockerfiles using the client's deployment pipelines.
- Deployed agents are automatically registered in Enterprise Advantage Agentic Studio.

### Integration patterns

The boilerplate implementations in this repository are built with the following features when configured for integration with the Enterprise Advantage platform:

- Agents are exposed via the A2A protocol using JSON RPC or JSON REST synchronous communication.
- Agents are automatically registered in a selected Agentic App Studio application on start-up.
- Agents are integrated with the platform's observability using OTEL instrumentation.
- Agents use the platform's LLM endpoints and models.
- Agents are integrated to Enterprise Advantage MCP Gateway (IBM Context Forge) with registration of a selected virtual server.

  | Category             | Feature / Capability            | Implementation Details                                                      |
  | -------------------- | ------------------------------- | --------------------------------------------------------------------------- |
  | Communication        | A2A Protocol Exposure           | JSON-RPC or JSON REST (synchronous)                                         |
  | Lifecycle            | Auto Registration               | Registers in selected Agentic App Studio app on startup                     |
  | Observability        | Telemetry Integration           | OpenTelemetry (OTEL) instrumentation                                        |
  | AI / LLM             | Model Integration               | Uses platform-provided LLM endpoints and models                             |
  | Platform Integration | MCP Gateway (IBM Context Forge) | Registers with Enterprise Advantage MCP Gateway via selected virtual server |

## Boilerplate Implementations

- [langgraph](langgraph/README.md) - multi-agent interface based on LangGraph
- [crewai_a2a](crewai_a2a/README.md) - multi-agent interface based on CrewAI
- [deepagent](deepagent)
  - [backend](deepagent/backend/README.md) - A2A agent based on LangChain's DeepAgent SDK
  - [frontend](deepagent/frontend/README.md) - custom frontend for the example agent
- [rlm](rlm/README.md) - A2A agent demonstrating Recursive Language Models (RLM) for processing long documents that exceed standard LLM context windows

Supporting tools:

- [frontend](frontend/README.md) - Simple chat UI that uses the A2A protocol to communicate with agents.
- [cli-client](cli-client/README.md) - A2A CLI client

## Repository initialization

To initialize a new repository with your chosen boilerplate template, you need to follow these steps and then execute the script below.

### Required input

The script will interactively ask for the following information:

- **Name of the Agent**
- **Project type** (`langgraph` or `crewai_a2a`)
- **Deployment platform (optional)** - this will generate **examples** of Kubernetes or Terraform files you may consider using. We do not provide support with deployment.
- **Git origin URL (optional)** - if you have a remote Github repository (e.g. on the IBM Github Enterprise instance), you can input the repository's URL and the new repository will be pushed to Github automatically.

### Prerequisites

You need to have:

- Git installed and available in PATH
- Bash available (`bash --version`)
- SSH access to `github.ibm.com` configured (if using SSH origin)

### Linux / macOS

To initialize a new repository, navigate to an empty folder and run the following script:

```bash
GIT_ORIGIN=git@github.ibm.com:Consulting-DTT-AI-Integration-Services/agentstudio-external-agent-boilerplate.git
TARGET_DIR=$(pwd); (
	trap 'rm -rf /tmp/.temp-repo' EXIT;
	rm -rf /tmp/.temp-repo \
	&& git clone --filter=blob:none --no-checkout $GIT_ORIGIN /tmp/.temp-repo \
	&& cd /tmp/.temp-repo && git sparse-checkout set scripts \
	&& git checkout && bash scripts/bin/init-repo.sh "$TARGET_DIR"
)
```

### Windows (recommended: WSL)

If you have WSL installed, run the Linux/macOS command above directly inside your WSL shell.

### Windows (PowerShell + Git Bash)

```powershell
$ErrorActionPreference = 'Stop'
$GIT_BASH = "${env:ProgramFiles}\Git\bin\bash.exe"
if (-not (Test-Path $GIT_BASH)) { $GIT_BASH = "${env:ProgramFiles(x86)}\Git\bin\bash.exe" }
if (-not (Test-Path $GIT_BASH)) { throw "Git Bash not found" }

$TARGET_DIR_WIN  = $PWD.Path
$TARGET_DIR_BASH = "/" + $TARGET_DIR_WIN.Substring(0,1).ToLower() + $TARGET_DIR_WIN.Substring(2).Replace('\','/')
$TEMP_REPO = Join-Path $env:TEMP '.temp-repo'
$GIT_ORIGIN = 'git@github.ibm.com:Consulting-DTT-AI-Integration-Services/agentstudio-external-agent-boilerplate.git'

try {
    if (Test-Path $TEMP_REPO) { Remove-Item $TEMP_REPO -Recurse -Force }
    git -c core.autocrlf=false clone --filter=blob:none --no-checkout $GIT_ORIGIN $TEMP_REPO
    Set-Location $TEMP_REPO
    git sparse-checkout init --cone
    git sparse-checkout set scripts
    git checkout

    & $GIT_BASH -lc "find scripts -type f -name '*.sh' -print0 | xargs -0 sed -i 's/\r$//'"
    & $GIT_BASH -x scripts/bin/init-repo.sh "$TARGET_DIR_BASH"
}
finally {
    Set-Location $env:TEMP
    if (Test-Path $TEMP_REPO) { Remove-Item $TEMP_REPO -Recurse -Force -ErrorAction SilentlyContinue }
    Set-Location $TARGET_DIR_WIN
}
```

### Result

After setup completes, your selected project is created from the boilerplate you chose. Follow the boilerplate's README for the exact local run steps and directory layout.

## Git hooks

This repository includes a repository-local pre-commit hook that runs checks for the three main parts of the repo: `frontend`, `langgraph` and `crewai_a2a`.

- Location: [.githooks/pre-commit](./.githooks/pre-commit)
- Helpers:
  - Install hooks: `scripts/install-git-hooks.sh` (sets `git config core.hooksPath .githooks`).
  - Run hook manually: `scripts/run-pre-commit.sh --all`.

What the hook runs:

- frontend
  - `npm audit`
  - `npm run lint`
  - `npm run format`
- langgraph
  - `make lint`
  - `make format`
- crewai_a2a
  - `make lint`
  - `make format`

Behavior:

- When invoked manually with `--all`, the hook runs checks for all three parts.
- When run as a git pre-commit hook (no args), it inspects the staged files and only runs checks for projects that have staged changes (for example, committing changes under `langgraph/` will run only the `langgraph` checks).

Temporarily disabling the hook:

- To skip the hook for a single commit, use `git commit --no-verify`.
- To disable repository-local hooks entirely, unset the hooks path:

```bash
git config --unset core.hooksPath
```

Or run `scripts/install-git-hooks.sh` again to restore the hook path.

