"""Tests for AgenticData runtime context and dispatch."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fabric import AgenticData
from agentic_fabric.runners.registry import RuntimeUnavailableError


def test_agentic_data_preserves_value_and_runtime_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """AgenticData should keep data and active runtime context together."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "langgraph")

    data = AgenticData({"task": "summarize"})
    data.use_runtime("langgraph")
    data.cast({"task": "rewrite"})

    assert data.active_runtime == "langgraph"
    assert data.as_builtin() == {"task": "rewrite"}


def test_use_runtime_strict_reports_install_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable runtimes should raise a typed error with install guidance."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: False)

    with pytest.raises(RuntimeUnavailableError, match="agentic-fabric\\[crewai\\]"):
        AgenticData().use_runtime("crewai")


def test_select_runtime_prefers_explicit_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit runtime selection should override an active runtime."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "strands")

    data = AgenticData(active_runtime="langgraph")

    assert data.select_runtime("strands") == "strands"


def test_select_runtime_rejects_active_manifest_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Active runtime and required manifest runtime should not silently conflict."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    data = AgenticData(active_runtime="langgraph")

    with pytest.raises(ValueError, match="conflicts"):
        data.select_runtime(crew_config={"required_framework": "crewai"})


def test_run_agent_uses_registered_crew_and_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Named agents should route through run_crew_auto with merged inputs."""
    calls: list[tuple[dict[str, Any], dict[str, Any], str | None]] = []

    def fake_run_crew_auto(crew_config: dict[str, Any], inputs: dict[str, Any], framework: str | None = None) -> str:
        calls.append((crew_config, inputs, framework))
        return "done"

    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "crewai")
    monkeypatch.setattr("agentic_fabric.core.decomposer.run_crew_auto", fake_run_crew_auto)

    data = AgenticData(agent_registry={"reviewer": {"name": "review", "agents": {}, "tasks": {}}})

    result = data.run_reviewer({"code": "x"}, severity="high")

    assert result == "done"
    assert calls == [({"name": "review", "agents": {}, "tasks": {}}, {"code": "x", "severity": "high"}, "crewai")]


def test_unknown_agent_lists_registered_names() -> None:
    """Unknown agent errors should include the registered names."""
    data = AgenticData(agent_registry={"reviewer": {"name": "review"}})

    with pytest.raises(KeyError, match="reviewer"):
        data.run_agent("writer")


def test_fallback_vendor_guidance_when_vendor_fabric_missing() -> None:
    """The no-vendor fallback should fail with install guidance."""
    data = AgenticData()
    if data.vendor_fabric_available:
        pytest.skip("vendor-fabric is installed in this environment")

    with pytest.raises(ImportError, match="vendor-fabric"):
        data.open("github")
