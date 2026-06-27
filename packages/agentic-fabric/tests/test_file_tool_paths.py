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


def test_workspace_root_resolution_uses_workspace_env_and_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Workspace discovery should fall back from package roots to env vars and cwd."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    workspace_root = tmp_path / "workspace"
    target_package = workspace_root / "packages" / "otterfall"
    target_package.mkdir(parents=True)
    monkeypatch.setattr(file_tools, "_find_workspace_root", lambda: workspace_root)

    assert file_tools.get_workspace_root() == target_package

    env_root = tmp_path / "env-root"
    env_root.mkdir()
    monkeypatch.setattr(file_tools, "_find_workspace_root", lambda: None)
    monkeypatch.setenv("OTTERFALL_ROOT", str(env_root))

    assert file_tools.get_workspace_root("otterfall") == env_root

    monkeypatch.delenv("OTTERFALL_ROOT")
    monkeypatch.chdir(tmp_path)

    assert file_tools.get_workspace_root("otterfall") == tmp_path


def test_find_workspace_root_finds_repository_root(monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker-file search should find the checked-out workspace root."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)

    root = file_tools._find_workspace_root()

    assert root is not None
    assert (root / "pyproject.toml").exists()
    assert (root / "packages").is_dir()


def test_find_workspace_root_returns_none_without_markers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The marker-file search should return None for installed modules outside a workspace."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    module_path = tmp_path / "installed" / "file_tools.py"
    module_path.parent.mkdir()
    module_path.write_text("# module\n", encoding="utf-8")
    monkeypatch.setattr(file_tools, "__file__", str(module_path))

    assert file_tools._find_workspace_root() is None


def test_clean_relative_path_rejects_invalid_values(monkeypatch: pytest.MonkeyPatch) -> None:
    """Relative path cleaning should reject empty, absolute, and traversal paths."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)

    for value in ("", "/tmp/file.ts", "src/../secret.ts"):
        with pytest.raises(ValueError, match="Path traversal not allowed"):
            file_tools._clean_relative_path(value)


def test_file_tools_write_read_and_list_allowed_workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CrewAI file tools should operate inside the resolved workspace root."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: workspace_root)

    write_result = file_tools.GameCodeWriterTool()._run("src/ecs/data/species.ts", "export const species = [];")
    read_result = file_tools.GameCodeReaderTool()._run("src/ecs/data/species.ts")
    list_result = file_tools.DirectoryListTool()._run("src/ecs/data")

    assert "Successfully wrote" in write_result
    assert read_result == "export const species = [];"
    assert "species.ts" in list_result


def test_file_tools_report_common_user_errors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Runtime tool errors should be returned as agent-readable strings."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir()
    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: workspace_root)

    bad_write_dir = file_tools.GameCodeWriterTool()._run("src/forbidden/file.ts", "")
    bad_write_ext = file_tools.GameCodeWriterTool()._run("src/ecs/data/file.py", "")
    missing_read = file_tools.GameCodeReaderTool()._run("src/ecs/data/missing.ts")
    missing_dir = file_tools.DirectoryListTool()._run("src/ecs/data")

    assert "not in an allowed directory" in bad_write_dir
    assert "Extension '.py' not allowed" in bad_write_ext
    assert "File not found" in missing_read
    assert "Directory not found" in missing_dir


def test_file_tools_report_reader_and_lister_edge_cases(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Reader and lister should report directories, large files, files, and empty directories."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)
    workspace_root = tmp_path / "workspace"
    data_dir = workspace_root / "src" / "ecs" / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(file_tools, "get_workspace_root", lambda: workspace_root)

    (data_dir / "folder").mkdir()
    large_file = data_dir / "large.ts"
    large_file.write_text("x" * 100_001, encoding="utf-8")
    empty_dir = data_dir / "empty"
    empty_dir.mkdir()
    (data_dir / ".hidden.ts").write_text("hidden", encoding="utf-8")
    (data_dir / "visible.ts").write_text("visible", encoding="utf-8")

    assert "Path is not a file" in file_tools.GameCodeReaderTool()._run("src/ecs/data/folder")
    assert "File too large" in file_tools.GameCodeReaderTool()._run("src/ecs/data/large.ts")
    assert "Path is not a directory" in file_tools.DirectoryListTool()._run("src/ecs/data/visible.ts")
    assert file_tools.DirectoryListTool()._run("src/ecs/data/empty") == "Directory src/ecs/data/empty is empty"

    list_result = file_tools.DirectoryListTool()._run("src/ecs/data")
    assert "visible.ts" in list_result
    assert ".hidden.ts" not in list_result


def test_file_tools_convert_permission_and_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tool exceptions should be converted to agent-readable strings."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)

    def raise_permission(path_value: str) -> tuple[str, Path]:
        raise PermissionError

    monkeypatch.setattr(file_tools, "_resolve_workspace_path", raise_permission)

    assert "Permission denied writing" in file_tools.GameCodeWriterTool()._run("src/ecs/data/file.ts", "")
    assert "Permission denied reading" in file_tools.GameCodeReaderTool()._run("src/ecs/data/file.ts")
    assert "Permission denied accessing" in file_tools.DirectoryListTool()._run("src/ecs/data")

    def raise_unexpected(path_value: str) -> tuple[str, Path]:
        raise RuntimeError("boom")

    monkeypatch.setattr(file_tools, "_resolve_workspace_path", raise_unexpected)

    assert "Error writing file: boom" in file_tools.GameCodeWriterTool()._run("src/ecs/data/file.ts", "")
    assert "Error reading file: boom" in file_tools.GameCodeReaderTool()._run("src/ecs/data/file.ts")
    assert "Error listing directory: boom" in file_tools.DirectoryListTool()._run("src/ecs/data")


def test_file_tools_convert_path_validation_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """ValueError path validation failures should be returned as agent-readable errors."""
    file_tools = import_file_tools_with_fake_crewai(monkeypatch)

    def raise_value_error(path_value: str) -> tuple[str, Path]:
        raise ValueError("bad path")

    monkeypatch.setattr(file_tools, "_resolve_workspace_path", raise_value_error)

    assert file_tools.GameCodeWriterTool()._run("../file.ts", "") == "Error: bad path"
    assert file_tools.GameCodeReaderTool()._run("../file.ts") == "Error: bad path"
    assert file_tools.DirectoryListTool()._run("../") == "Error: bad path"
