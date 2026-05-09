import asyncio
from collections import defaultdict
from typing import Any

import boto3

import rlm.clients as _rlm_clients
from rlm.clients.base_lm import BaseLM
from rlm.core.types import ModelUsageSummary, UsageSummary


class BedrockClient(BaseLM):
    """
    LM Client for running models via Amazon Bedrock's Converse API.

    Uses boto3 for synchronous calls and runs them in a thread pool for async
    support. Credentials are resolved from environment variables or the default
    boto3 credential chain (IAM role, ~/.aws/credentials, etc.).

    Environment variables:
        AWS_REGION            – AWS region (default: us-east-1)
        AWS_ACCESS_KEY_ID     – AWS access key ID
        AWS_SECRET_ACCESS_KEY – AWS secret access key
        AWS_SESSION_TOKEN     – Optional session token for temporary credentials
    """

    def __init__(
        self,
        modelId: str | None = None,
        region: str | None = None,
        accessKeyId: str | None = None,
        secretAccessKey: str | None = None,
        **kwargs,
    ):
        super().__init__(model_name=modelId, **kwargs)

        self.region = region or "us-east-1"
        self.model_name = modelId

        session = boto3.Session(
            aws_access_key_id=accessKeyId or None,
            aws_secret_access_key=secretAccessKey or None,
            region_name=self.region,
        )
        self.client = session.client("bedrock-runtime")

        # Per-model usage tracking
        self.model_call_counts: dict[str, int] = defaultdict(int)
        self.model_input_tokens: dict[str, int] = defaultdict(int)
        self.model_output_tokens: dict[str, int] = defaultdict(int)
        self.model_total_tokens: dict[str, int] = defaultdict(int)

        # Last-call tracking (populated by _track_usage)
        self.last_prompt_tokens: int = 0
        self.last_completion_tokens: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_messages(prompt: str | list[dict[str, Any]]) -> list[dict]:
        """Convert a plain string or OpenAI-style message list to Bedrock format."""
        if isinstance(prompt, str):
            return [{"role": "user", "content": [{"text": prompt}]}]
        if isinstance(prompt, list) and all(isinstance(m, dict) for m in prompt):
            messages = []
            for msg in prompt:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                # Bedrock Converse only accepts "user" and "assistant" roles.
                if role == "system":
                    # Prepend system content as a user turn if no explicit system
                    # prompt block is provided (Bedrock handles system separately).
                    role = "user"
                if isinstance(content, str):
                    messages.append({"role": role, "content": [{"text": content}]})
                elif isinstance(content, list):
                    # Already structured content blocks – pass through.
                    messages.append({"role": role, "content": content})
                else:
                    messages.append({"role": role, "content": [{"text": str(content)}]})
            return messages
        raise ValueError(f"Invalid prompt type: {type(prompt)}")

    @staticmethod
    def _extract_system_prompt(prompt: str | list[dict[str, Any]]) -> list[dict] | None:
        """Extract system messages for the Bedrock system parameter."""
        if not isinstance(prompt, list):
            return None
        system_texts = [
            m["content"] for m in prompt
            if m.get("role") == "system" and isinstance(m.get("content"), str)
        ]
        if system_texts:
            return [{"text": "\n".join(system_texts)}]
        return None

    def _call_converse(self, model: str, prompt: str | list[dict[str, Any]]) -> dict:
        """Execute a synchronous Bedrock Converse API call."""
        messages = self._build_messages(prompt)
        system = self._extract_system_prompt(prompt)

        kwargs: dict[str, Any] = {
            "modelId": model,
            "messages": messages,
        }
        if system:
            kwargs["system"] = system

        return self.client.converse(**kwargs)

    def _track_usage(self, response: dict, model: str) -> None:
        usage = response.get("usage", {})
        input_tokens = usage.get("inputTokens", 0)
        output_tokens = usage.get("outputTokens", 0)
        total_tokens = usage.get("totalTokens", input_tokens + output_tokens)

        self.model_call_counts[model] += 1
        self.model_input_tokens[model] += input_tokens
        self.model_output_tokens[model] += output_tokens
        self.model_total_tokens[model] += total_tokens

        self.last_prompt_tokens = input_tokens
        self.last_completion_tokens = output_tokens

    @staticmethod
    def _extract_text(response: dict) -> str:
        """Pull the assistant text out of a Converse response."""
        output = response.get("output", {})
        message = output.get("message", {})
        content = message.get("content", [])
        texts = [block["text"] for block in content if "text" in block]
        return "\n".join(texts)

    # ------------------------------------------------------------------
    # BaseLM interface
    # ------------------------------------------------------------------

    def completion(self, prompt: str | list[dict[str, Any]], model: str | None = None) -> str:
        model = model or self.model_name
        if not model:
            raise ValueError("Model name is required for BedrockClient.")

        response = self._call_converse(model, prompt)
        self._track_usage(response, model)
        return self._extract_text(response)

    async def acompletion(
        self, prompt: str | list[dict[str, Any]], model: str | None = None
    ) -> str:
        model = model or self.model_name
        if not model:
            raise ValueError("Model name is required for BedrockClient.")

        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(None, self._call_converse, model, prompt)
        self._track_usage(response, model)
        return self._extract_text(response)

    def get_usage_summary(self) -> UsageSummary:
        model_summaries = {}
        for model in self.model_call_counts:
            model_summaries[model] = ModelUsageSummary(
                total_calls=self.model_call_counts[model],
                total_input_tokens=self.model_input_tokens[model],
                total_output_tokens=self.model_output_tokens[model],
                total_cost=None,  # Bedrock does not return cost in API responses
            )
        return UsageSummary(model_usage_summaries=model_summaries)

    def get_last_usage(self) -> ModelUsageSummary:
        return ModelUsageSummary(
            total_calls=1,
            total_input_tokens=self.last_prompt_tokens,
            total_output_tokens=self.last_completion_tokens,
            total_cost=None,
        )


# Register "bedrock" as a backend so RLM can discover it via get_client.
# Patch both the module attribute and the already-imported reference in rlm.core.rlm.
import rlm.core.rlm as _rlm_core

_original_get_client = _rlm_clients.get_client


def _patched_get_client(backend, backend_kwargs):
    if backend == "bedrock":
        return BedrockClient(**backend_kwargs)
    return _original_get_client(backend, backend_kwargs)


_rlm_clients.get_client = _patched_get_client
_rlm_core.get_client = _patched_get_client
