"""LLM configuration shared by all runners.

Uses Anthropic Claude directly via ANTHROPIC_API_KEY.
Falls back to OpenRouter if OPENROUTER_API_KEY is set.
Supports local Ollama via OLLAMA_BASE_URL / AGENTIC_FABRIC_LLM_PROVIDER=ollama.
"""

from __future__ import annotations

import os

from dataclasses import dataclass
from enum import Enum


try:
    from crewai import LLM
except ImportError:
    # Allow module to load even if crewai not installed (for testing)
    LLM = None  # type: ignore[assignment]


class LLMProvider(Enum):
    """Available LLM providers."""

    ANTHROPIC = "anthropic"
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"


@dataclass(frozen=True)
class LLMConfig:
    """Configuration for specific LLM use cases."""

    model: str
    temperature: float
    description: str


# Model identifiers
_CLAUDE_HAIKU_45 = "claude-haiku-4-5-20251001"
_CLAUDE_SONNET_45 = "claude-sonnet-4-5-20250929"
_CLAUDE_SONNET_4 = "claude-sonnet-4-20250514"
_CLAUDE_OPUS_4 = "claude-opus-4-20250514"

# Default model - Claude Haiku 4.5 for fast, cost-effective operations
DEFAULT_MODEL = _CLAUDE_HAIKU_45

# Default Ollama model for local testing (small, fast, instruction-tuned)
_DEFAULT_OLLAMA_MODEL = "qwen2.5:0.5b"

# Alternative models
MODELS = {
    "haiku": _CLAUDE_HAIKU_45,
    "sonnet": _CLAUDE_SONNET_45,
    "sonnet-4": _CLAUDE_SONNET_4,
    "opus": _CLAUDE_OPUS_4,
    # OpenRouter fallbacks
    "openrouter-auto": "openrouter/auto",
    "openrouter-haiku": "openrouter/anthropic/claude-haiku-4.5",
    # Ollama
    "ollama": _DEFAULT_OLLAMA_MODEL,
    "ollama-coder": "codellama",
}

_OPENROUTER_MODEL_MAP = {
    _CLAUDE_HAIKU_45: "openrouter/anthropic/claude-haiku-4.5",
    _CLAUDE_SONNET_45: "openrouter/anthropic/claude-sonnet-4.5",
    _CLAUDE_SONNET_4: "openrouter/anthropic/claude-sonnet-4",
    _CLAUDE_OPUS_4: "openrouter/anthropic/claude-opus-4",
    "haiku": "openrouter/anthropic/claude-haiku-4.5",
    "sonnet": "openrouter/anthropic/claude-sonnet-4.5",
    "sonnet-4": "openrouter/anthropic/claude-sonnet-4",
    "opus": "openrouter/anthropic/claude-opus-4",
}

# Predefined configurations for common use cases
LLM_CONFIGS = {
    "reasoning": LLMConfig(model=_CLAUDE_OPUS_4, temperature=0.3, description="Optimized for complex reasoning tasks"),
    "creative": LLMConfig(
        model=_CLAUDE_SONNET_45,
        temperature=0.8,
        description="Optimized for creative content generation",
    ),
    "code": LLMConfig(
        model=_CLAUDE_SONNET_45,
        temperature=0.2,
        description="Optimized for code generation and analysis",
    ),
    "default": LLMConfig(
        model=_CLAUDE_HAIKU_45,
        temperature=0.7,
        description="Balanced configuration for general use",
    ),
}


def _is_ollama_mode() -> bool:
    """Return whether Ollama is the configured LLM provider."""
    return (
        os.getenv("AGENTIC_FABRIC_LLM_PROVIDER", "").lower() == "ollama"
        or bool(os.getenv("OLLAMA_BASE_URL"))
    )


def _get_ollama_model() -> str:
    """Return the configured Ollama model."""
    return os.getenv("OLLAMA_MODEL", _DEFAULT_OLLAMA_MODEL)


def _get_ollama_base_url() -> str:
    """Return the Ollama server URL."""
    return os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_llm(model: str = DEFAULT_MODEL, temperature: float = 0.7, provider: LLMProvider | None = None) -> LLM | None:
    """Get configured LLM instance for agents.

    Args:
        model: Model identifier. Defaults to claude-haiku-4-5-20251001 (DEFAULT_MODEL)
        temperature: Sampling temperature (0.0-1.0). Lower = more focused,
                    higher = more creative.
        provider: Force specific provider (ANTHROPIC, OPENROUTER, or OLLAMA).
                 If None, auto-detects based on available API keys and env vars.

    Available models:
        - claude-haiku-4-5-20251001 (default - fast, cost-effective)
        - claude-sonnet-4-5-20250929 (best for code and creative)
        - claude-sonnet-4-20250514 (capable general purpose)
        - claude-opus-4-20250514 (most capable)
        - openrouter/auto (fallback via OpenRouter)
        - qwen2.5:0.5b (local Ollama, no API key needed)

    Returns:
        Configured LLM instance, or None if no API key set

    Note:
        Tries ANTHROPIC_API_KEY first, falls back to OPENROUTER_API_KEY.
        When AGENTIC_FABRIC_LLM_PROVIDER=ollama or OLLAMA_BASE_URL is set,
        routes to a local Ollama server (no API key needed).
        Returns None if no provider is configured.

    Example:
        >>> llm = get_llm()  # Uses Claude Haiku 4.5
        >>> llm = get_llm("claude-opus-4-20250514", temperature=0.3)
        >>> llm = get_llm(provider=LLMProvider.OPENROUTER)
        >>> llm = get_llm(provider=LLMProvider.OLLAMA)  # Local Ollama
    """
    if LLM is None:
        return None

    # Force provider if specified
    if provider == LLMProvider.OLLAMA or _is_ollama_mode():
        return _create_ollama_llm(model if model != DEFAULT_MODEL else _get_ollama_model(), temperature)

    if provider == LLMProvider.ANTHROPIC:
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            return None
        return _create_anthropic_llm(model, temperature, anthropic_key)

    if provider == LLMProvider.OPENROUTER:
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_key:
            return None
        return _create_openrouter_llm(model, temperature, openrouter_key)

    # Auto-detect: Try Anthropic first for direct Claude models
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key and not model.startswith("openrouter/"):
        return _create_anthropic_llm(model, temperature, anthropic_key)

    # Fall back to OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if openrouter_key:
        return _create_openrouter_llm(model, temperature, openrouter_key)

    return None


def _create_anthropic_llm(model: str, temperature: float, api_key: str) -> LLM:
    """Create Anthropic LLM instance."""
    return LLM(
        model=model,
        api_key=api_key,
        temperature=temperature,
    )


def _create_openrouter_llm(model: str, temperature: float, api_key: str) -> LLM:
    """Create OpenRouter LLM instance."""
    # Convert model name to OpenRouter format if needed
    if not model.startswith("openrouter/"):
        model = _OPENROUTER_MODEL_MAP.get(model, MODELS.get(model, MODELS.get("openrouter-auto", "openrouter/auto")))

    return LLM(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=temperature,
    )


def _create_ollama_llm(model: str, temperature: float) -> LLM:
    """Create Ollama LLM instance (local, no API key needed)."""
    base_url = _get_ollama_base_url()
    # litellm (used by CrewAI LLM) routes to Ollama via ollama_chat/ prefix
    ollama_model = model if model.startswith("ollama") else f"ollama_chat/{model}"
    return LLM(
        model=ollama_model,
        base_url=base_url,
        temperature=temperature,
    )


def get_llm_or_raise(model: str = DEFAULT_MODEL, temperature: float = 0.7, provider: LLMProvider | None = None) -> LLM:
    """Get configured LLM instance, raising if API key not set.

    Use this when you need to ensure an LLM is available.

    Args:
        model: Model identifier (see get_llm for options)
        temperature: Sampling temperature (0.0-1.0)
        provider: Force specific provider (optional)

    Returns:
        Configured LLM instance

    Raises:
        ValueError: If neither ANTHROPIC_API_KEY nor OPENROUTER_API_KEY is set,
                    and Ollama mode is not enabled.
    """
    llm = get_llm(model, temperature, provider)
    if llm is None:
        raise ValueError(
            "ANTHROPIC_API_KEY or OPENROUTER_API_KEY environment variable must be set, "
            "or AGENTIC_FABRIC_LLM_PROVIDER=ollama with OLLAMA_BASE_URL. "
            "Get Anthropic key at https://console.anthropic.com/ or "
            "OpenRouter key at https://openrouter.ai/ or "
            "install Ollama from https://ollama.com/"
        )
    return llm


def get_llm_for_task(task: str) -> LLM | None:
    """Get LLM configured for a specific task type.

    Args:
        task: Task type - one of: 'reasoning', 'creative', 'code', 'default'

    Returns:
        Configured LLM instance, or None if no API key set

    Raises:
        ValueError: If task type is unknown

    Example:
        >>> llm = get_llm_for_task('code')  # Low temp, optimized for code
        >>> llm = get_llm_for_task('creative')  # High temp, creative output
    """
    if task not in LLM_CONFIGS:
        raise ValueError(f"Unknown task type: {task}. Available: {', '.join(LLM_CONFIGS.keys())}")

    config = LLM_CONFIGS[task]
    return get_llm(config.model, config.temperature)


# Convenience functions for specific use cases (backward compatibility)
def get_reasoning_llm() -> LLM | None:
    """Get LLM optimized for complex reasoning tasks."""
    return get_llm_for_task("reasoning")


def get_creative_llm() -> LLM | None:
    """Get LLM optimized for creative tasks."""
    return get_llm_for_task("creative")


def get_code_llm() -> LLM | None:
    """Get LLM optimized for code generation."""
    return get_llm_for_task("code")
