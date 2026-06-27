"""Tests for LLM provider selection helpers."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fabric.config import llm as llm_config
from agentic_fabric.config.llm import LLMProvider


class FakeLLM:
    """Small stand-in for CrewAI's LLM wrapper."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


def clear_llm_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove provider credentials installed by the autouse test fixture."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)


def enable_fake_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the fake LLM constructor for provider-selection tests."""
    monkeypatch.setattr(llm_config, "LLM", FakeLLM)


def test_get_llm_returns_none_when_constructor_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    monkeypatch.setattr(llm_config, "LLM", None)

    assert llm_config.get_llm() is None


def test_get_llm_returns_none_without_provider_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)

    assert llm_config.get_llm() is None


def test_get_llm_prefers_anthropic_for_direct_models(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    result = llm_config.get_llm("claude-sonnet-4-20250514", temperature=0.2)

    assert isinstance(result, FakeLLM)
    assert result.kwargs == {
        "model": "claude-sonnet-4-20250514",
        "api_key": "anthropic-key",
        "temperature": 0.2,
    }


def test_get_llm_can_force_openrouter_and_normalizes_model(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    result = llm_config.get_llm(
        "claude-sonnet-4-20250514",
        temperature=0.4,
        provider=LLMProvider.OPENROUTER,
    )

    assert isinstance(result, FakeLLM)
    assert result.kwargs == {
        "model": "openrouter/anthropic/claude-sonnet-4",
        "api_key": "openrouter-key",
        "base_url": "https://openrouter.ai/api/v1",
        "temperature": 0.4,
    }


def test_get_llm_can_force_anthropic(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")

    result = llm_config.get_llm("claude-haiku-4-5-20251001", temperature=0.1, provider=LLMProvider.ANTHROPIC)

    assert isinstance(result, FakeLLM)
    assert result.kwargs == {
        "model": "claude-haiku-4-5-20251001",
        "api_key": "anthropic-key",
        "temperature": 0.1,
    }


def test_get_llm_preserves_openrouter_model_in_auto_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    result = llm_config.get_llm("openrouter/anthropic/claude-haiku-4.5")

    assert isinstance(result, FakeLLM)
    assert result.kwargs["model"] == "openrouter/anthropic/claude-haiku-4.5"
    assert result.kwargs["api_key"] == "openrouter-key"
    assert result.kwargs["base_url"] == "https://openrouter.ai/api/v1"


def test_forced_providers_require_matching_key(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-key")

    assert llm_config.get_llm(provider=LLMProvider.OPENROUTER) is None

    monkeypatch.delenv("ANTHROPIC_API_KEY")
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    assert llm_config.get_llm(provider=LLMProvider.ANTHROPIC) is None


def test_get_llm_or_raise_reports_install_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY or OPENROUTER_API_KEY"):
        llm_config.get_llm_or_raise()


def test_get_llm_or_raise_returns_configured_llm(monkeypatch: pytest.MonkeyPatch) -> None:
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "openrouter-key")

    result = llm_config.get_llm_or_raise(provider=LLMProvider.OPENROUTER)

    assert isinstance(result, FakeLLM)
    assert result.kwargs["api_key"] == "openrouter-key"


def test_task_helpers_use_declared_configs(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, float]] = []

    def fake_get_llm(model: str, temperature: float, provider: LLMProvider | None = None) -> str:
        calls.append((model, temperature))
        assert provider is None
        return "llm"

    monkeypatch.setattr(llm_config, "get_llm", fake_get_llm)

    assert llm_config.get_llm_for_task("code") == "llm"
    assert calls == [(llm_config.LLM_CONFIGS["code"].model, llm_config.LLM_CONFIGS["code"].temperature)]
    assert llm_config.get_reasoning_llm() == "llm"
    assert llm_config.get_creative_llm() == "llm"
    assert llm_config.get_code_llm() == "llm"


def test_get_llm_for_task_rejects_unknown_task() -> None:
    with pytest.raises(ValueError, match="Unknown task type: unknown"):
        llm_config.get_llm_for_task("unknown")


class TestOllamaProvider:
    """Tests for the Ollama LLM provider path."""

    def test_is_ollama_mode_true_when_ollama_base_url_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OLLAMA_BASE_URL should enable ollama mode."""
        monkeypatch.delenv("AGENTIC_FABRIC_LLM_PROVIDER", raising=False)
        monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

        assert llm_config._is_ollama_mode() is True

    def test_is_ollama_mode_true_when_provider_env_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AGENTIC_FABRIC_LLM_PROVIDER=ollama should enable ollama mode."""
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.setenv("AGENTIC_FABRIC_LLM_PROVIDER", "ollama")

        assert llm_config._is_ollama_mode() is True

    def test_is_ollama_mode_false_by_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without env config, ollama mode is off."""
        monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
        monkeypatch.delenv("AGENTIC_FABRIC_LLM_PROVIDER", raising=False)

        assert llm_config._is_ollama_mode() is False

    def test_get_ollama_model_returns_env_when_set(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """OLLAMA_MODEL env var should override the default."""
        monkeypatch.setenv("OLLAMA_MODEL", "llama3:8b")

        assert llm_config._get_ollama_model() == "llama3:8b"

    def test_get_ollama_model_returns_default_when_unset(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Missing OLLAMA_MODEL should fall back to the bundled default."""
        monkeypatch.delenv("OLLAMA_MODEL", raising=False)

        assert llm_config._get_ollama_model() == llm_config._DEFAULT_OLLAMA_MODEL


def test_get_llm_with_explicit_ollama_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """provider=LLMProvider.OLLAMA should build an ollama LLM regardless of env."""
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("AGENTIC_FABRIC_LLM_PROVIDER", raising=False)

    result = llm_config.get_llm(provider=LLMProvider.OLLAMA)

    assert isinstance(result, FakeLLM)
    assert result.kwargs["model"].startswith("ollama_chat/")
    assert "base_url" in result.kwargs


def test_get_llm_auto_detects_ollama_when_base_url_set(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without explicit provider, OLLAMA_BASE_URL should auto-route to Ollama."""
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OLLAMA_MODEL", "qwen2.5:0.5b")
    monkeypatch.delenv("AGENTIC_FABRIC_LLM_PROVIDER", raising=False)

    result = llm_config.get_llm()

    assert isinstance(result, FakeLLM)
    assert result.kwargs["model"].startswith("ollama_chat/")


def test_get_llm_or_raise_mentions_ollama_when_no_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """The install-guidance error should mention Ollama as an alternative."""
    clear_llm_env(monkeypatch)
    enable_fake_llm(monkeypatch)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("AGENTIC_FABRIC_LLM_PROVIDER", raising=False)

    with pytest.raises(ValueError, match="ollama"):
        llm_config.get_llm_or_raise()
