"""Package initializer for `crewai_a2a`.

Set a safe default `MODEL` environment variable early so the
`crewai` LLM factory selects the Bedrock native provider instead of
defaulting to OpenAI during module imports. This runs before any
submodule imports (e.g. `flow`, `agents`).
"""
