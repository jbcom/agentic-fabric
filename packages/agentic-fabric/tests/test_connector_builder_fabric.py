"""Tests for the connector-builder fabric agent."""

from __future__ import annotations

import builtins
import importlib
import sys
import types

from typing import Any

import pytest


class FakeAgent:
    """Capture Agent constructor kwargs."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls.append(kwargs)


class FakeTask:
    """Capture Task constructor kwargs."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls.append(kwargs)


class FakeCrew:
    """Capture Crew constructor kwargs and kickoff input."""

    calls: list[dict[str, Any]] = []

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.calls.append(kwargs)
        self.kickoff_inputs: dict[str, Any] | None = None

    def kickoff(self, inputs: dict[str, Any]) -> Any:
        self.kickoff_inputs = inputs
        return "Success"


def import_connector_builder_with_fake_crewai(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Import the connector builder module with fake CrewAI classes installed."""
    FakeAgent.calls.clear()
    FakeTask.calls.clear()
    FakeCrew.calls.clear()

    fake_crewai = types.ModuleType("crewai")
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    sys.modules.pop("agentic_fabric.fabric_agents.connector_builder.connector_builder_fabric", None)
    return importlib.import_module("agentic_fabric.fabric_agents.connector_builder.connector_builder_fabric")


@pytest.fixture
def connector_builder_module(monkeypatch: pytest.MonkeyPatch):
    """Yield a connector-builder module backed by fake CrewAI classes."""
    module = import_connector_builder_with_fake_crewai(monkeypatch)
    yield module
    sys.modules.pop("agentic_fabric.fabric_agents.connector_builder.connector_builder_fabric", None)


def test_connector_builder_fabric_initializes_and_kicks_off(
    monkeypatch: pytest.MonkeyPatch,
    connector_builder_module: Any,
) -> None:
    """ConnectorBuilderFabricAgent should build configured agents/tasks and delegate kickoff."""
    module = connector_builder_module
    monkeypatch.setattr(module, "resolve_tools", lambda tools: [f"resolved:{tool}" for tool in tools])

    fabric_agent_instance = module.ConnectorBuilderFabricAgent(output_dir="test_output")

    assert len(FakeAgent.calls) == 3
    assert len(FakeTask.calls) == 3
    assert isinstance(fabric_agent_instance.fabric_agent, FakeCrew)
    assert FakeAgent.calls[0]["tools"] == ["resolved:ScrapeWebsiteTool", "resolved:CrawlWebsiteTool"]
    assert FakeAgent.calls[2]["tools"] == ["resolved:FileWriteTool"]
    assert "test_output directory" in FakeTask.calls[2]["description"]
    assert FakeCrew.calls[0]["agents"] == [
        fabric_agent_instance.doc_scraper,
        fabric_agent_instance.api_analyzer,
        fabric_agent_instance.code_generator,
    ]
    assert FakeCrew.calls[0]["tasks"] == [
        fabric_agent_instance.scrape_docs,
        fabric_agent_instance.analyze_api,
        fabric_agent_instance.generate_code,
    ]

    result = fabric_agent_instance.kickoff(inputs={"url": "http://example.com"})

    assert result == "Success"
    assert fabric_agent_instance.fabric_agent.kickoff_inputs == {"url": "http://example.com"}


def test_connector_builder_kickoff_returns_raw_result(
    monkeypatch: pytest.MonkeyPatch,
    connector_builder_module: Any,
) -> None:
    """CrewAI raw results should be returned without string conversion."""
    module = connector_builder_module

    class RawCrew(FakeCrew):
        def kickoff(self, inputs: dict[str, Any]) -> Any:
            self.kickoff_inputs = inputs
            return types.SimpleNamespace(raw="raw success")

    monkeypatch.setattr(module, "Crew", RawCrew)
    monkeypatch.setattr(module, "resolve_tools", lambda tools: [])

    fabric_agent_instance = module.ConnectorBuilderFabricAgent()

    assert fabric_agent_instance.kickoff(inputs={"url": "http://example.com"}) == "raw success"


def test_connector_builder_reports_missing_crewai(monkeypatch: pytest.MonkeyPatch) -> None:
    """Connector builder should raise install guidance when CrewAI is absent."""
    module = import_connector_builder_with_fake_crewai(monkeypatch)
    monkeypatch.delitem(sys.modules, "crewai", raising=False)
    module.Agent = None
    module.Crew = None
    module.Task = None

    original_import = builtins.__import__

    def reject_crewai(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "crewai":
            raise ImportError("missing crewai")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_crewai)

    with pytest.raises(RuntimeError, match="pip install crewai"):
        module._load_crewai_classes()
