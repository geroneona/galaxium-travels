"""Model configuration: aliases and agent -> model mappings.

This module centralises model ARNs and agent mappings so callers can
lookup which Bedrock model an agent should use.
"""

from __future__ import annotations

from typing import Dict, Mapping


MODEL_ALIASES: Dict[str, Mapping[str, str]] = {
    "nova_micro": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/global.amazon.nova-2-lite-v1:0",
        "input_format": "text",
        "model_family": "nova",
    },
    "nova_lite": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.amazon.nova-2-lite-v1:0",
        "input_format": "text",
        "model_family": "nova",
    },
    "nova_pro": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.amazon.nova-pro-v1:0",
        "input_format": "text",
        "model_family": "nova",
    },
    "claude_sonnet": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.anthropic.claude-sonnet-4-5-20250929-v1:0",
        "input_format": "messages",
        "model_family": "anthropic",
    },
    "claude_haiku": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.anthropic.claude-haiku-4-5-20251001-v1:0",
        "input_format": "messages",
        "model_family": "anthropic",
    },
    "claude_opus": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.anthropic.claude-opus-4-5-20251101-v1:0",
        "input_format": "messages",
        "model_family": "anthropic",
    },
    "llama3_2_1b": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.meta.llama3-2-1b-instruct-v1:0",
        "input_format": "text",
        "model_family": "llama",
    },
    "llama3_2_3b": {
        "platform": "Bedrock",
        "inference": "profile",
        "arn": "arn:aws:bedrock:<REGION>:<ACCOUNT_ID>:inference-profile/eu.meta.llama3-2-3b-instruct-v1:0",
        "input_format": "text",
        "model_family": "llama",
    },
}


__all__ = ["MODEL_ALIASES"]
