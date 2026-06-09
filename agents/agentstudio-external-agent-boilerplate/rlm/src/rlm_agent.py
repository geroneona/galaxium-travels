from rlm import RLM
from rlm.utils.prompts import RLM_SYSTEM_PROMPT

# not referenced in this file, but the import is needed to initialize patch the list of available backends and add bedrock
from .bedrock_rlm_adapter import BedrockClient
from .logger import get_logger
from agentstudio_sdk.agentic_apps_api import agentic_apps_api

logger = get_logger(__name__)

def _load_context(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _create_rlm() -> RLM:
    """Create an RLM instance backed by the model from ICA platform settings."""

    credentials = agentic_apps_api.get_model_credentials('claude-sonnet')

    logger.info("Loaded ICA model: %s (region=%s)", credentials["modelId"], credentials["region"])

    return RLM(
        backend="bedrock",
        backend_kwargs=credentials,
        verbose=True,
        custom_system_prompt=(
            "You are an example agent who demonstrates Recoursive Language Models (RLMs) capabilities. \n"
            "The main strength of RLMs is the ability to process very long context that exceeds the model's context window size many times. \n"
            "As an example of a long context you have a book called 'Clarissa' by Samuel Richardson. It is one of the longest novels in the English language free of copyright.\n"
            "If user's input is clearly unrelated to the context respond directly without reading context by assigning your response to a variable 'final_answer' and call FINAL_VAR('final_answer')\n\n"
            "For inputs unrelated to the context, include in your response reminder of what your purpose is, say you are example agent that demonstrates RLM and your example context is a book Clarissa.\n"
            "IF the user's input is related to the context, continue by the following instructions: \n\n"
            + RLM_SYSTEM_PROMPT
        )
    )

rlm_context: str = _load_context("./data/clarissa.txt")
rlm = _create_rlm()
