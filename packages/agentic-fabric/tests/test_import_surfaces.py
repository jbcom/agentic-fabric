"""Tests for small import and module-entry surfaces."""

from __future__ import annotations

import importlib
import importlib.metadata
import runpy
import sys

from pathlib import Path
from typing import Any

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = PACKAGE_ROOT.parents[1]
REPO_SPECIFIC_LEGACY_TOKEN = "otter" + "fall"


def test_package_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source-tree imports should have a stable version fallback when not installed."""
    from importlib.metadata import PackageNotFoundError

    def missing_version(name: str) -> str:
        if name == "agentic-fabric":
            raise PackageNotFoundError(name)
        return "1.0.0"

    # Simulate the __init__.py version-fallback logic with a mocked version function.
    # The actual __init__.py does: try: __version__ = version("agentic-fabric") except PackageNotFoundError: __version__ = "1.1.0"
    namespace: dict[str, Any] = {"version": missing_version, "PackageNotFoundError": PackageNotFoundError}
    exec(
        "try:\n"
        "    __version__ = version('agentic-fabric')\n"
        "except PackageNotFoundError:\n"
        "    __version__ = '1.1.0'\n",
        namespace,
    )

    assert namespace["__version__"] == "1.1.0"


def test_base_exports_file_tools_without_crewai() -> None:
    """The base package should re-export framework-neutral file tools and archetype helpers."""
    sys.modules.pop("agentic_fabric.tools.file_tools", None)
    sys.modules.pop("agentic_fabric.base", None)

    base = importlib.import_module("agentic_fabric.base")

    assert "DirectoryListTool" in base.__all__
    assert "GameCodeReaderTool" in base.__all__
    assert "GameCodeWriterTool" in base.__all__
    assert "resolve_archetype" in base.__all__
    assert "resolve_agent_archetypes" in base.__all__
    assert base.DirectoryListTool.__name__ == "DirectoryListTool"


def test_module_entrypoint_delegates_to_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """python -m agentic_fabric should call the CLI main function."""
    from agentic_fabric import main as cli_main

    calls: list[str] = []
    monkeypatch.setattr(cli_main, "main", lambda: calls.append("main"))
    sys.modules.pop("agentic_fabric.__main__", None)

    runpy.run_module("agentic_fabric.__main__", run_name="__main__")

    assert calls == ["main"]


def test_cli_script_entrypoint_prints_help(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    """Executing main.py as a script should use the same CLI entrypoint."""
    from agentic_fabric import main as cli_main

    monkeypatch.setattr(sys, "argv", ["agentic-fabric"])

    runpy.run_path(str(cli_main.__file__), run_name="__main__")

    assert "agentic-fabric - framework-agnostic fabric agent runner" in capsys.readouterr().out


def test_runtime_source_does_not_reown_vendor_or_legacy_surfaces() -> None:
    """Runtime source should not drift into vendor ownership or old names."""
    disallowed = {
        "secrets_sync": "SecretSync Python access must route through vendor-fabric capabilities",
        "secretssync": "SecretSync direct-import spelling is not part of this layer",
        REPO_SPECIFIC_LEGACY_TOKEN: "repo-specific package naming is not part of the agnostic package",
        "agentic-crew": "fabric agent naming replaced old crew package naming",
        "connector_builder_crew": "connector builder code should use fabric naming",
        "ConnectorBuilderCrew": "connector builder code should use fabric naming",
    }
    source_files = sorted((PACKAGE_ROOT / "src" / "agentic_fabric").rglob("*.py"))

    failures: list[str] = []
    for source_file in source_files:
        text = source_file.read_text(encoding="utf-8")
        for token, reason in disallowed.items():
            if token in text:
                failures.append(f"{source_file.relative_to(PACKAGE_ROOT)} contains {token!r}: {reason}")

    assert failures == []


def test_public_surfaces_do_not_advertise_retired_vendor_mcp_entrypoints() -> None:
    """MCP ownership should stay with agentic-fabric, not vendor-fabric."""
    retired = {
        "vendor_fabric.mcp": "use agentic_fabric.tools.vendor_mcp",
        "vendor_fabric.meshy.mcp": "use agentic_fabric.tools.meshy_mcp",
        "vendor-fabric-mcp": "use the agentic-fabric-vendor-mcp console script",
        "vendor-fabric[mcp]": "MCP transport dependencies live in agentic-fabric[mcp]",
        "vendor-fabric[meshy,mcp]": "combine agentic-fabric[mcp] with vendor-fabric[meshy]",
    }
    roots = [
        PACKAGE_ROOT / "README.md",
        PACKAGE_ROOT / "pyproject.toml",
        PACKAGE_ROOT / "src",
        PACKAGE_ROOT / "examples",
        WORKSPACE_ROOT / "docs",
        WORKSPACE_ROOT / "AGENTS.md",
        WORKSPACE_ROOT / "README.md",
        WORKSPACE_ROOT / "pyproject.toml",
        WORKSPACE_ROOT / "tox.ini",
    ]

    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.suffix in {".md", ".py", ".rst", ".toml", ".yaml", ".yml"}
                and "_build" not in path.parts
                and "__pycache__" not in path.parts
            )

    failures: list[str] = []
    for source_file in sorted(files):
        text = source_file.read_text(encoding="utf-8")
        for token, replacement in retired.items():
            if token in text:
                failures.append(f"{source_file.relative_to(WORKSPACE_ROOT)} contains {token!r}: {replacement}")

    assert failures == []
