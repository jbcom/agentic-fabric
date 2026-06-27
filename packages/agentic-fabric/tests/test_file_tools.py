"""Tests for framework-neutral file manipulation tools."""

from __future__ import annotations

import builtins
import importlib
import os
import sys

from pathlib import Path
from unittest.mock import patch

import pytest


@pytest.fixture(autouse=True)
def fresh_file_tools_module():
    """Keep import-branch assertions isolated between tests."""
    sys.modules.pop("agentic_fabric.tools.file_tools", None)
    yield
    sys.modules.pop("agentic_fabric.tools.file_tools", None)


def test_file_tools_import_without_optional_frameworks(monkeypatch: pytest.MonkeyPatch) -> None:
    """Built-in tools should not require CrewAI or Pydantic at import time."""
    real_import = builtins.__import__

    def block_optional_imports(name: str, *args, **kwargs):
        if name in {"crewai.tools", "pydantic"}:
            raise ImportError(name)
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", block_optional_imports)

    from agentic_fabric.tools.file_tools import GameCodeReaderTool, GameCodeWriterTool

    assert GameCodeReaderTool().args_schema is None
    assert GameCodeWriterTool()._run("forbidden/example.ts", "").startswith("Error:")


class TestGetWorkspaceRoot:
    """Tests for get_workspace_root function."""

    def test_uses_target_package_env_var(self, temp_workspace: Path) -> None:
        """Test that TARGET_PACKAGE env var is respected."""
        from agentic_fabric.tools.file_tools import get_workspace_root

        # Create another package
        other_pkg = temp_workspace / "packages" / "other_package"
        other_pkg.mkdir(parents=True)

        # Create pyproject.toml at workspace root
        (temp_workspace / "pyproject.toml").write_text("[project]\nname = 'test'")

        with (
            patch.dict(os.environ, {"TARGET_PACKAGE": "other_package"}),
            patch(
                "agentic_fabric.tools.file_tools._find_workspace_root",
                return_value=temp_workspace,
            ),
        ):
            root = get_workspace_root()

        assert root == other_pkg

    def test_defaults_to_single_workspace_package(self, tmp_path: Path) -> None:
        """A single package workspace should be selected without repo-specific names."""
        from agentic_fabric.tools.file_tools import get_workspace_root

        target_package = tmp_path / "packages" / "sample"
        target_package.mkdir(parents=True, exist_ok=True)

        with patch(
            "agentic_fabric.tools.file_tools._find_workspace_root",
            return_value=tmp_path,
        ):
            # Remove TARGET_PACKAGE if set
            env = os.environ.copy()
            env.pop("TARGET_PACKAGE", None)
            with patch.dict(os.environ, env, clear=True):
                root = get_workspace_root()

        assert root == target_package

    def test_explicit_package_name(self, temp_workspace: Path) -> None:
        """Test explicit package name parameter."""
        from agentic_fabric.tools.file_tools import get_workspace_root

        # Create custom package
        custom_pkg = temp_workspace / "packages" / "custom"
        custom_pkg.mkdir(parents=True)

        with patch(
            "agentic_fabric.tools.file_tools._find_workspace_root",
            return_value=temp_workspace,
        ):
            root = get_workspace_root(package_name="custom")

        assert root == custom_pkg


class TestGameCodeWriterTool:
    """Tests for GameCodeWriterTool."""

    def test_rejects_path_traversal(self) -> None:
        """Test that path traversal is rejected."""
        from agentic_fabric.tools.file_tools import GameCodeWriterTool

        tool = GameCodeWriterTool()
        result = tool._run(file_path="../../../etc/passwd", content="malicious")

        assert "Error" in result
        assert "Path traversal" in result or "not allowed" in result

    def test_rejects_absolute_paths(self) -> None:
        """Test that absolute paths are rejected."""
        from agentic_fabric.tools.file_tools import GameCodeWriterTool

        tool = GameCodeWriterTool()
        result = tool._run(file_path="/etc/passwd", content="malicious")

        assert "Error" in result

    def test_rejects_disallowed_directories(self) -> None:
        """Test that writes to non-allowed directories are rejected."""
        from agentic_fabric.tools.file_tools import GameCodeWriterTool

        tool = GameCodeWriterTool()
        result = tool._run(file_path="node_modules/test.ts", content="test")

        assert "Error" in result
        assert "not in an allowed directory" in result

    def test_rejects_disallowed_extensions(self) -> None:
        """Test that disallowed file extensions are rejected."""
        from agentic_fabric.tools.file_tools import GameCodeWriterTool

        tool = GameCodeWriterTool()
        result = tool._run(file_path="src/ecs/test.exe", content="binary")

        assert "Error" in result
        assert "not allowed" in result

    def test_writes_to_allowed_directory(self, temp_workspace: Path) -> None:
        """Test that writing to allowed directories works."""
        from agentic_fabric.tools.file_tools import GameCodeWriterTool

        # Create the allowed directory structure
        ecs_dir = temp_workspace / "packages" / "sample" / "src" / "ecs"
        ecs_dir.mkdir(parents=True)

        tool = GameCodeWriterTool()

        with patch(
            "agentic_fabric.tools.file_tools.get_workspace_root",
            return_value=temp_workspace / "packages" / "sample",
        ):
            result = tool._run(
                file_path="src/ecs/TestComponent.ts",
                content="export const TestComponent = {};",
            )

        assert "Successfully wrote" in result
        assert (ecs_dir / "TestComponent.ts").exists()
        assert (ecs_dir / "TestComponent.ts").read_text(encoding="utf-8") == "export const TestComponent = {};"


class TestGameCodeReaderTool:
    """Tests for GameCodeReaderTool."""

    def test_rejects_path_traversal(self) -> None:
        """Test that path traversal is rejected."""
        from agentic_fabric.tools.file_tools import GameCodeReaderTool

        tool = GameCodeReaderTool()
        result = tool._run(file_path="../../../etc/passwd")

        assert "Error" in result
        assert "not allowed" in result

    def test_reads_existing_file(self, temp_workspace: Path) -> None:
        """Test reading an existing file."""
        from agentic_fabric.tools.file_tools import GameCodeReaderTool

        # Create a test file
        test_file = temp_workspace / "packages" / "sample" / "src" / "test.ts"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("export const Test = 'hello';")

        tool = GameCodeReaderTool()

        with patch(
            "agentic_fabric.tools.file_tools.get_workspace_root",
            return_value=temp_workspace / "packages" / "sample",
        ):
            result = tool._run(file_path="src/test.ts")

        assert "export const Test" in result

    def test_returns_error_for_missing_file(self, temp_workspace: Path) -> None:
        """Test that missing files return an error."""
        from agentic_fabric.tools.file_tools import GameCodeReaderTool

        tool = GameCodeReaderTool()

        with patch(
            "agentic_fabric.tools.file_tools.get_workspace_root",
            return_value=temp_workspace / "packages" / "sample",
        ):
            result = tool._run(file_path="src/nonexistent.ts")

        assert "Error" in result
        assert "not found" in result


class TestDirectoryListTool:
    """Tests for DirectoryListTool."""

    def test_lists_directory_contents(self, temp_workspace: Path) -> None:
        """Test listing directory contents."""
        from agentic_fabric.tools.file_tools import DirectoryListTool

        # Create some test files
        src_dir = temp_workspace / "packages" / "sample" / "src"
        src_dir.mkdir(parents=True)
        (src_dir / "index.ts").write_text("export {};")
        (src_dir / "utils").mkdir()

        tool = DirectoryListTool()

        with patch(
            "agentic_fabric.tools.file_tools.get_workspace_root",
            return_value=temp_workspace / "packages" / "sample",
        ):
            result = tool._run(directory="src")

        assert "index.ts" in result
        assert "utils" in result

    def test_rejects_path_traversal(self) -> None:
        """Test that path traversal is rejected."""
        from agentic_fabric.tools.file_tools import DirectoryListTool

        tool = DirectoryListTool()
        result = tool._run(directory="../../../etc")

        assert "Error" in result
        assert "not allowed" in result


class TestConfigureWriteRestrictions:
    """Tests for configure_write_restrictions and env-var overrides."""

    def test_configure_write_restrictions_replaces_allowed_dirs(self) -> None:
        """configure_write_restrictions should replace the allowed write dirs list."""
        from agentic_fabric.tools.file_tools import ALLOWED_WRITE_DIRS, configure_write_restrictions

        original = list(ALLOWED_WRITE_DIRS)
        try:
            configure_write_restrictions(allowed_dirs=["custom/dir"])
            assert list(ALLOWED_WRITE_DIRS) == ["custom/dir"]
        finally:
            configure_write_restrictions(allowed_dirs=original)

    def test_configure_write_restrictions_replaces_allowed_extensions(self) -> None:
        """configure_write_restrictions should replace the allowed extensions set."""
        from agentic_fabric.tools.file_tools import ALLOWED_EXTENSIONS, configure_write_restrictions

        original = set(ALLOWED_EXTENSIONS)
        try:
            configure_write_restrictions(allowed_extensions={".py", ".toml"})
            assert set(ALLOWED_EXTENSIONS) == {".py", ".toml"}
        finally:
            configure_write_restrictions(allowed_extensions=original)

    def test_configure_write_restrictions_leaves_unchanged_when_none(self) -> None:
        """Passing None for an argument should leave that restriction unchanged."""
        from agentic_fabric.tools.file_tools import ALLOWED_WRITE_DIRS, configure_write_restrictions

        before_dirs = list(ALLOWED_WRITE_DIRS)
        try:
            configure_write_restrictions(allowed_dirs=None, allowed_extensions=None)
            assert list(ALLOWED_WRITE_DIRS) == before_dirs
        finally:
            configure_write_restrictions(allowed_dirs=before_dirs)

    def test_env_dirs_override_default_allowed_write_dirs(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """AGENTIC_FABRIC_WRITE_DIRS env var should override the defaults at import time."""
        monkeypatch.setenv("AGENTIC_FABRIC_WRITE_DIRS", "src/python,src/config")
        sys.modules.pop("agentic_fabric.tools.file_tools", None)
        try:
            module = importlib.import_module("agentic_fabric.tools.file_tools")

            assert module.ALLOWED_WRITE_DIRS == ["src/python", "src/config"]
        finally:
            sys.modules.pop("agentic_fabric.tools.file_tools", None)
            monkeypatch.delenv("AGENTIC_FABRIC_WRITE_DIRS", raising=False)

    def test_env_extensions_override_default_allowed_extensions(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AGENTIC_FABRIC_WRITE_EXTENSIONS env var should override the defaults at import time."""
        monkeypatch.setenv("AGENTIC_FABRIC_WRITE_EXTENSIONS", ".py,.toml")
        sys.modules.pop("agentic_fabric.tools.file_tools", None)
        try:
            module = importlib.import_module("agentic_fabric.tools.file_tools")

            assert {".py", ".toml"} == module.ALLOWED_EXTENSIONS
        finally:
            sys.modules.pop("agentic_fabric.tools.file_tools", None)
            monkeypatch.delenv("AGENTIC_FABRIC_WRITE_EXTENSIONS", raising=False)
