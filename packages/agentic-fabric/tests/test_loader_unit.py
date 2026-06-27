"""CrewAI loader tests that do not require the optional CrewAI package."""

from __future__ import annotations

import importlib
import sys
import types

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest


class FakeAgent:
    """Capture CrewAI Agent constructor kwargs."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeTask:
    """Capture CrewAI Task constructor kwargs."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeCrew:
    """Capture CrewAI Crew constructor kwargs."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs


class FakeProcess:
    """Small stand-in for CrewAI Process."""

    sequential = "sequential"


class FakeKnowledgeSource:
    """Capture knowledge source file paths."""

    def __init__(self, file_paths: list[str]) -> None:
        self.file_paths = file_paths


@pytest.fixture
def loader_with_fake_crewai(monkeypatch: pytest.MonkeyPatch) -> Generator[Any, None, None]:
    """Import the loader with fake CrewAI modules installed."""
    fake_crewai = types.ModuleType("crewai")
    fake_crewai.Agent = FakeAgent
    fake_crewai.Task = FakeTask
    fake_crewai.Crew = FakeCrew
    fake_crewai.Process = FakeProcess

    fake_tools = types.ModuleType("crewai.tools")

    class BaseTool:
        """Minimal stand-in for crewai.tools.BaseTool."""

    fake_tools.BaseTool = BaseTool

    fake_knowledge = types.ModuleType("crewai.knowledge")
    fake_knowledge.__path__ = []
    fake_source = types.ModuleType("crewai.knowledge.source")
    fake_source.__path__ = []
    fake_text_source = types.ModuleType("crewai.knowledge.source.text_file_knowledge_source")
    fake_text_source.TextFileKnowledgeSource = FakeKnowledgeSource

    for module_name, module in {
        "crewai": fake_crewai,
        "crewai.tools": fake_tools,
        "crewai.knowledge": fake_knowledge,
        "crewai.knowledge.source": fake_source,
        "crewai.knowledge.source.text_file_knowledge_source": fake_text_source,
    }.items():
        monkeypatch.setitem(sys.modules, module_name, module)

    sys.modules.pop("agentic_fabric.core.loader", None)
    sys.modules.pop("agentic_fabric.tools.file_tools", None)
    loader = importlib.import_module("agentic_fabric.core.loader")

    yield loader

    sys.modules.pop("agentic_fabric.core.loader", None)
    sys.modules.pop("agentic_fabric.tools.file_tools", None)


def test_load_knowledge_sources_reads_supported_nonempty_files(
    loader_with_fake_crewai: Any,
    tmp_path: Path,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    note = knowledge_dir / "note.md"
    note.write_text("# Useful context", encoding="utf-8")
    (knowledge_dir / "empty.py").write_text("   ", encoding="utf-8")
    (knowledge_dir / "ignored.txt").write_text("not supported", encoding="utf-8")

    sources = loader_with_fake_crewai.load_knowledge_sources([knowledge_dir, tmp_path / "missing"])

    assert len(sources) == 1
    assert sources[0].file_paths == [str(note)]


def test_load_knowledge_sources_logs_unreadable_files(
    loader_with_fake_crewai: Any,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    bad_file = knowledge_dir / "bad.md"
    bad_file.write_text("content", encoding="utf-8")

    def broken_content_check(path: Path) -> bool:
        if path == bad_file:
            raise OSError("boom")
        return True

    monkeypatch.setattr(loader_with_fake_crewai, "_has_non_whitespace_content", broken_content_check)

    assert loader_with_fake_crewai.load_knowledge_sources([knowledge_dir]) == []
    assert "Could not load knowledge source" in caplog.text


def test_create_agent_and_task_from_config(loader_with_fake_crewai: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel_llm = object()
    monkeypatch.setattr("agentic_fabric.config.llm.get_llm", lambda: sentinel_llm)

    agent = loader_with_fake_crewai.create_agent_from_config("writer", {"goal": "write"}, tools=["tool"])
    task = loader_with_fake_crewai.create_task_from_config("draft", {"description": "draft"}, agent)

    assert isinstance(agent, FakeAgent)
    assert agent.kwargs["role"] == "writer"
    assert agent.kwargs["goal"] == "write"
    assert agent.kwargs["backstory"] == ""
    assert agent.kwargs["llm"] is sentinel_llm
    assert agent.kwargs["tools"] == ["tool"]
    assert agent.kwargs["allow_delegation"] is False
    assert task.kwargs["description"] == "draft"
    assert task.kwargs["expected_output"] == ""
    assert task.kwargs["agent"] is agent


def test_load_fabric_agent_from_config_resolves_tools_and_fallbacks(
    loader_with_fake_crewai: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("agentic_fabric.config.llm.get_llm", lambda: None)
    monkeypatch.setattr(loader_with_fake_crewai, "load_knowledge_sources", lambda paths: ["knowledge"])
    monkeypatch.setattr(
        loader_with_fake_crewai,
        "resolve_tools",
        lambda tool_names: ["resolved-tool"] if tool_names else [],
    )

    fabric_agent = loader_with_fake_crewai.load_fabric_agent_from_config(
        {
            "agents": {
                "tool_user": {"role": "Tool User", "tools": ["registered"]},
                "engineer": {"role": "Engineer"},
                "researcher": {"role": "Researcher"},
            },
            "tasks": {
                "tool_task": {"description": "use a tool", "agent": "tool_user"},
                "build_task": {"description": "build", "agent": "engineer"},
                "research_task": {"description": "read", "agent": "researcher"},
            },
            "knowledge_paths": [Path("knowledge")],
        }
    )

    assert isinstance(fabric_agent, FakeCrew)
    assert fabric_agent.kwargs["process"] == "sequential"
    assert fabric_agent.kwargs["planning"] is True
    assert fabric_agent.kwargs["memory"] is True
    assert fabric_agent.kwargs["knowledge_sources"] == ["knowledge"]

    agents = fabric_agent.kwargs["agents"]
    assert [agent.kwargs["role"] for agent in agents] == ["Tool User", "Engineer", "Researcher"]
    assert agents[0].kwargs["tools"] == ["resolved-tool"]
    assert len(agents[1].kwargs["tools"]) == 2
    assert len(agents[2].kwargs["tools"]) == 2
    assert len(fabric_agent.kwargs["tasks"]) == 3


def test_load_fabric_agent_from_config_respects_explicit_null_tools(
    loader_with_fake_crewai: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An agent with ``tools: null`` in YAML should get an empty tools list."""
    monkeypatch.setattr("agentic_fabric.config.llm.get_llm", lambda: None)
    monkeypatch.setattr(loader_with_fake_crewai, "load_knowledge_sources", lambda paths: [])
    monkeypatch.setattr(
        loader_with_fake_crewai,
        "resolve_tools",
        lambda tool_names: ["resolved"] if tool_names else [],
    )

    fabric_agent = loader_with_fake_crewai.load_fabric_agent_from_config(
        {
            "agents": {
                "null_tools_agent": {"role": "Agent", "tools": None},
                "no_tools_key": {"role": "Reader"},
            },
            "tasks": {
                "task1": {"description": "do", "agent": "null_tools_agent"},
                "task2": {"description": "read", "agent": "no_tools_key"},
            },
            "knowledge_paths": [],
        }
    )

    agents = fabric_agent.kwargs["agents"]
    # tools: null → empty list (explicit)
    assert agents[0].kwargs["tools"] == []
    # no tools key → read_tools fallback
    assert len(agents[1].kwargs["tools"]) == 2


def test_load_fabric_agent_from_config_requires_task_agent(loader_with_fake_crewai: Any) -> None:
    with pytest.raises(ValueError, match="missing an 'agent' assignment"):
        loader_with_fake_crewai.load_fabric_agent_from_config(
            {
                "agents": {"writer": {"role": "Writer"}},
                "tasks": {"draft": {"description": "draft"}},
            }
        )


def test_load_fabric_agent_from_config_requires_existing_agent(loader_with_fake_crewai: Any) -> None:
    with pytest.raises(ValueError, match="Agent 'missing' for task 'draft' not found"):
        loader_with_fake_crewai.load_fabric_agent_from_config(
            {
                "agents": {"writer": {"role": "Writer"}},
                "tasks": {"draft": {"description": "draft", "agent": "missing"}},
            }
        )


def test_load_fabric_agent_respects_explicit_empty_tools_list(
    loader_with_fake_crewai: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An agent with an explicit empty ``tools: []`` should get no tools.

    The loader should distinguish between "no tools key" (use the read-only
    default file tools) and "explicit empty list" (respect the empty list).
    """
    monkeypatch.setattr("agentic_fabric.config.llm.get_llm", lambda: None)
    monkeypatch.setattr(loader_with_fake_crewai, "load_knowledge_sources", lambda paths: [])
    monkeypatch.setattr(
        loader_with_fake_crewai,
        "resolve_tools",
        lambda tool_names: ["resolved-tool"] if tool_names else [],
    )

    fabric_agent = loader_with_fake_crewai.load_fabric_agent_from_config(
        {
            "agents": {
                "explicit_empty": {"role": "Explicit Empty", "tools": []},
                "no_tools_key": {"role": "No Tools Key"},
            },
            "tasks": {},
            "knowledge_paths": [],
        }
    )

    agents = fabric_agent.kwargs["agents"]
    explicit_empty_agent = next(a for a in agents if a.kwargs["role"] == "Explicit Empty")
    no_tools_key_agent = next(a for a in agents if a.kwargs["role"] == "No Tools Key")

    assert explicit_empty_agent.kwargs["tools"] == []
    assert len(no_tools_key_agent.kwargs["tools"]) == 2
