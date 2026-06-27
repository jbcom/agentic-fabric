"""Tests for agent capability metadata and dispatch."""

from __future__ import annotations

from typing import Any

import pytest

from agentic_fabric.capabilities import (
    AgentCapabilityProviderMixin,
    AgentCapabilitySpec,
    agent_capability,
    tool_capability,
)
from agentic_fabric.runners.base import BaseRunner


class TestCapabilityCollection:
    """Capability decorators should be collected at class creation."""

    def test_base_runner_declares_runtime_capabilities(self) -> None:
        """Runner methods should expose read-only capability metadata."""

        class TestRunner(BaseRunner):
            def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
                return fabric_agent_config

            def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
                return f"{fabric_agent}:{inputs}"

            def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
                return agent_config

            def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
                return task_config, agent

        runner = TestRunner()

        assert "build_fabric_agent" in runner.capability_map()
        assert "run_fabric_agent" in runner.capability_map()
        assert runner.call_capability("run_fabric_agent", {"name": "fabric_agent"}, {"task": "go"}) == "{'name': 'fabric_agent'}:{'task': 'go'}"

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

    def test_capability_metadata_and_kind_filtering(self) -> None:
        """Capability metadata should serialize and filter by kind."""

        class ToolProvider(AgentCapabilityProviderMixin):
            @tool_capability("read_file", aliases=("read",), description="Read a file.")
            def read_file(self) -> str:
                return "content"

        provider = ToolProvider()
        specs = provider.list_capabilities(kind="tool")

        assert specs == (provider.agent_capabilities["read_file"],)
        assert specs[0].as_dict() == {
            "name": "read_file",
            "kind": "tool",
            "aliases": ["read"],
            "description": "Read a file.",
        }
        assert AgentCapabilitySpec("run").as_dict()["kind"] == "runtime"

    def test_capability_dispatch_reports_unknown_and_noncallable(self) -> None:
        """Capability dispatch should fail clearly for invalid names and methods."""

        class BrokenProvider(AgentCapabilityProviderMixin):
            @agent_capability("broken")
            def broken(self) -> str:
                return "ok"

        provider = BrokenProvider()

        with pytest.raises(AttributeError, match="Unknown agent capability: missing"):
            provider.call_capability("missing")

        provider.broken = "not callable"  # type: ignore[method-assign]

        with pytest.raises(TypeError, match="not callable"):
            provider.call_capability("broken")
