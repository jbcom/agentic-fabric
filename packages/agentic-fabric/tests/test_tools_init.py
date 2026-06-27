"""Tests for lazy tool package exports."""

from __future__ import annotations

import builtins

from typing import Any

import pytest

from agentic_fabric import tools


class FakeTool:
    """Constructible fake tool used by lazy loader tests."""


def test_getattr_lazily_loads_declared_tool(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str]] = []

    def fake_load_attr(module_name: str, attr_name: str) -> type[FakeTool]:
        calls.append((module_name, attr_name))
        return FakeTool

    monkeypatch.setattr(tools, "_load_attr", fake_load_attr)

    assert tools.__getattr__("GameCodeReaderTool") is FakeTool
    assert tools.__getattr__("ScrapeWebsiteTool") is FakeTool
    assert calls == [
        ("agentic_fabric.tools.file_tools", "GameCodeReaderTool"),
        ("agentic_fabric.tools.scraping_tools", "ScrapeWebsiteTool"),
    ]


def test_getattr_rejects_unknown_name() -> None:
    with pytest.raises(AttributeError, match="does-not-exist"):
        tools.__getattr__("does-not-exist")


def test_tool_collection_helpers_instantiate_lazy_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_load_attr(module_name: str, attr_name: str) -> type[FakeTool]:
        assert module_name in {"agentic_fabric.tools.file_tools", "agentic_fabric.tools.scraping_tools"}
        assert attr_name.endswith("Tool")
        return FakeTool

    monkeypatch.setattr(tools, "_load_attr", fake_load_attr)

    file_tools = tools.get_file_tools()
    scraping_tools = tools.get_scraping_tools()

    assert len(file_tools) == 3
    assert all(isinstance(tool, FakeTool) for tool in file_tools)
    assert len(scraping_tools) == 2
    assert all(isinstance(tool, FakeTool) for tool in scraping_tools)


def test_get_all_tools_suppresses_unavailable_optional_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "get_file_tools", lambda: ["file"])
    monkeypatch.setattr(tools, "get_scraping_tools", lambda: (_ for _ in ()).throw(ImportError("missing scraping")))
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mesh_toolkit.agent_tools.crewai":
            raise ImportError("missing meshy")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert tools.get_all_tools() == ["file"]


def test_get_all_tools_includes_meshy_tools_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "get_file_tools", lambda: ["file"])
    monkeypatch.setattr(tools, "get_scraping_tools", lambda: ["scrape"])
    real_import = builtins.__import__

    class FakeMeshModule:
        @staticmethod
        def get_tools() -> list[str]:
            return ["mesh"]

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "mesh_toolkit.agent_tools.crewai":
            return FakeMeshModule
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert tools.get_all_tools() == ["file", "scrape", "mesh"]
