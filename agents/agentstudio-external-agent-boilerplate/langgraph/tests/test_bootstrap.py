import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.bootstrap import build_adapters  # noqa: E402


class FakeLLM:
    def __init__(self, provider: str, model: str):
        self.provider = provider
        self.model = model


def test_build_adapters_skips_non_dict_config_entries():
    adapters = build_adapters(
        {
            "meal": {"provider": "aws", "model": "claude"},
            "invalid": "not-a-dict",
        },
        llm_factory=FakeLLM,
    )

    assert list(adapters) == ["meal"]
    assert adapters["meal"].provider == "aws"
    assert adapters["meal"].model == "claude"


def test_build_adapters_requires_provider_and_model():
    try:
        build_adapters({"meal": {"provider": "aws"}}, llm_factory=FakeLLM)
    except RuntimeError as exc:
        assert str(exc) == (
            "agent 'meal' configuration must include non-empty 'provider' and 'model'"
        )
    else:
        raise AssertionError("build_adapters() should reject incomplete agent config")
