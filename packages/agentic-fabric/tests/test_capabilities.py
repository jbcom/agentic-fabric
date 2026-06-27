"""Tests for agent capability metadata and dispatch."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fabric.capabilities import agent_capability
from agentic_fabric.runners.base import BaseRunner


class TestCapabilityCollection:
    """Capability decorators should be collected at class creation."""

    def test_base_runner_declares_runtime_capabilities(self) -> None:
        """Runner methods should expose read-only capability metadata."""

        class TestRunner(BaseRunner):
            def build_crew(self, crew_config: dict[str, Any]) -> Any:
                return crew_config

            def run(self, crew: Any, inputs: dict[str, Any]) -> str:
                return f"{crew}:{inputs}"

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return agent_config

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return task_config, agent

        runner = TestRunner()

        assert "build_crew" in runner.capability_map()
        assert "run_crew" in runner.capability_map()
        assert runner.call_capability("run_crew", {"name": "crew"}, {"task": "go"}) == "{'name': 'crew'}:{'task': 'go'}"

        with pytest.raises(TypeError):
            runner.capability_map()["new"] = runner.capability_map()["run"]  # type: ignore[index]

    def test_subclass_decorator_adds_custom_capability(self) -> None:
        """Custom decorated methods should be dispatchable by alias."""

        class CustomProvider:
            @agent_capability("summarize", aliases=("summary",), description="Summarize text.")
            def summarize(self, text: str) -> str:
                return text.upper()

        from agentic_fabric.capabilities import AgentCapabilityProviderMixin

        class TestProvider(AgentCapabilityProviderMixin, CustomProvider):
            pass

        provider = TestProvider()

        assert provider.agent_capabilities["summary"].name == "summarize"
        assert provider.call_capability("summary", "hello") == "HELLO"
