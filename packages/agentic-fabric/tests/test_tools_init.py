"""Tests for lazy tool package exports."""

from __future__ import annotations

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
    assert tools.__getattr__("VendorCapabilityTool") is FakeTool
    assert calls == [
        ("agentic_fabric.tools.file_tools", "GameCodeReaderTool"),
        ("agentic_fabric.tools.scraping_tools", "ScrapeWebsiteTool"),
        ("agentic_fabric.tools.vendor", "VendorCapabilityTool"),
    ]


def test_load_attr_imports_module_attribute(monkeypatch: pytest.MonkeyPatch) -> None:
    imported: list[str] = []

    class FakeModule:
        Tool = FakeTool

    def fake_import_module(module_name: str) -> type[FakeModule]:
        imported.append(module_name)
        return FakeModule

    monkeypatch.setattr(tools, "import_module", fake_import_module)

    assert tools._load_attr("example.tools", "Tool") is FakeTool
    assert imported == ["example.tools"]


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
    monkeypatch.setattr(tools, "_load_attr", lambda *_: (_ for _ in ()).throw(RuntimeError("missing")))

    assert tools.get_all_tools() == ["file"]


def test_get_all_tools_includes_vendor_capability_tools_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tools, "get_file_tools", lambda: ["file"])
    monkeypatch.setattr(tools, "get_scraping_tools", lambda: ["scrape"])

    def fake_load_attr(module_name: str, attr_name: str) -> Any:
        assert module_name == "agentic_fabric.tools.vendor"
        assert attr_name == "vendor_capability_tools"
        return lambda **_: ["vendor"]

    monkeypatch.setattr(tools, "_load_attr", fake_load_attr)

    assert tools.get_all_tools() == ["file", "scrape", "vendor"]
