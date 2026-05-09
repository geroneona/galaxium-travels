
* The A2A agent server informs about health on path `/health` and readiness on path `/ready`
* The server serves the agent card.
    * On path: `/.well-known/agent-card.json`
    * On the legacy path path: `/.well-known/agent.json`
* The A2A agent responds to incoming messages without crashing
* The A2A agent is implemented with lanchain deepagent SDK, his capabilities are:
    * Parse CVs
    * Analyze job descriptions
    * Analyze skill gaps
    * Evaluate culture fit
    * Synthesis of report
* The backend supports runtime hooks for session start, input, output, error, tool call, tool result, and tool error events
