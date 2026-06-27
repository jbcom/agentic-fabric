"""Security tests for file tool path resolution helpers."""

from __future__ import annotations

import importlib
import sys
import types

from pathlib import Path

import pytest


def import_file_tools_with_fake_crewai(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Import file_tools without requiring the optional CrewAI package."""
    fake_crewai = types.ModuleType("crewai")
    fake_tools = types.ModuleType("crewai.tools")

    class BaseTool:
        """Minimal stand-in for crewai.tools.BaseTool."""

    fake_tools.BaseTool = BaseTool
    monkeypatch.setitem(sys.modules, "crewai", fake_crewai)
    monkeypatch.setitem(sys.modules, "crewai.tools", fake_tools)
    sys.modules.pop("agentic_fabric.tools.file_tools", None)
    return importlib.import_module("agentic_fabric.tools.file_tools")


def test_resolve_workspace_path_rejects_symlink_escape(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolved paths must remain below the workspace root after symlinks."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (workspace_root / "src").mkdir()
    (workspace_root / "src" / "ecs").symlink_to(outside, target_is_directory=True)

    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: workspace_root)

    with pytest.raises(ValueError, match="escapes workspace root"):
        file_tools._resolve_workspace_path("src/ecs/secret.ts")


def test_allowed_write_path_requires_directory_boundary(monkeypatch: pytest.MonkeyPatch) -> None:
    """Allowed write dirs match real path segments, not arbitrary prefixes."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)

    assert file_tools._is_allowed_write_path("src/ecs/component.ts")
    assert not file_tools._is_allowed_write_path("src/ecsnot/component.ts")
