"""Tests for small import and module-entry surfaces."""

from __future__ import annotations

import importlib
import importlib.metadata
import runpy
import sys

from pathlib import Path

import pytest


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def test_package_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source-tree imports should have a stable version fallback."""
    package_file = importlib.import_module("agentic_fabric").__file__

    def missing_version(name: str) -> str:
        if name == "agentic-fabric":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.0.0"

    monkeypatch.setattr(importlib.metadata, "version", missing_version)

    namespace = runpy.run_path(package_file, run_name="agentic_fabric_version_fallback")

    assert namespace["__version__"] == "0.0.0"


def test_base_exports_file_tools_without_crewai() -> None:
    """The base package should re-export framework-neutral file tools."""
    sys.modules.pop("agentic_fabric.tools.file_tools", None)
    sys.modules.pop("agentic_fabric.base", None)

    base = importlib.import_module("agentic_fabric.base")

    assert base.__all__ == ["DirectoryListTool", "GameCodeReaderTool", "GameCodeWriterTool"]
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
        "otterfall": "otterfall is repo-specific and not part of the agnostic package",
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
