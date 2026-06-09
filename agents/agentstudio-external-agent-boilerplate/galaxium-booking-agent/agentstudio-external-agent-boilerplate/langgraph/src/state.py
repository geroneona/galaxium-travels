from typing import Literal, TypedDict


class ConversationMessage(TypedDict):
    """A single conversation turn passed to the model."""

    role: Literal["user", "assistant"]
    content: str


class _RequiredAgentState(TypedDict):
    """Required keys for AgentState."""

    utterance: str


class AgentState(_RequiredAgentState, total=False):
    """State for the agent graph.

    Fields:
    - utterance: the user's input text (required)
    - messages: conversation history including the current user message (optional)
    - target: the chosen agent id (optional)
    - response: agent-generated reply text (optional)
    """

    messages: list[ConversationMessage]
    target: str
    response: str


__all__ = ["AgentState", "ConversationMessage"]
