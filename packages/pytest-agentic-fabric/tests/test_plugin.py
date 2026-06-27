"""Tests for pytest-agentic-fabric."""

from __future__ import annotations

import importlib
import importlib.metadata
import runpy

from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml


pytest_plugins = ("pytester",)


def test_package_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source-tree imports should have a stable version fallback."""
    package_file = importlib.import_module("pytest_agentic_fabric").__file__

    def missing_version(name: str) -> str:
        if name == "pytest-agentic-fabric":
            raise importlib.metadata.PackageNotFoundError(name)
        return "1.0.0"

    monkeypatch.setattr(importlib.metadata, "version", missing_version)

    namespace = runpy.run_path(package_file, run_name="pytest_agentic_fabric_version_fallback")

    assert namespace["__version__"] == "0.0.0"


def test_agentic_runtime_available_fixture(agentic_runtime_available: Callable[[str], bool]) -> None:
    """The runtime availability fixture should detect installed modules."""
    assert agentic_runtime_available("sys") is True
    assert agentic_runtime_available("module_that_should_not_exist_for_agentic_fabric_tests") is False


def test_agentic_runtime_registry_fixture(agentic_runtime_registry: dict[str, Any]) -> None:
    """The runtime registry fixture should be isolated and mutable."""
    agentic_runtime_registry["local"] = {"available": True}

    assert agentic_runtime_registry == {"local": {"available": True}}


def test_agentic_runtime_modules_fixture(agentic_runtime_modules: dict[str, tuple[str, ...]]) -> None:
    """Known runtime modules should be exposed for consumer tests."""
    assert agentic_runtime_modules["crewai"][0] == "crewai"
    assert "langgraph.prebuilt" in agentic_runtime_modules["langgraph"]
    assert agentic_runtime_modules["strands"] == ("strands",)


def test_agentic_mock_runtime_fixture(agentic_mock_runtime: Callable[[str], dict[str, ModuleType]]) -> None:
    """Runtime mocking fixture should install importable module objects."""
    modules = agentic_mock_runtime("langgraph")

    import langgraph.prebuilt

    assert modules["langgraph.prebuilt"] is langgraph.prebuilt
    assert langgraph.prebuilt.create_react_agent("llm", [])["args"] == ("llm", [])


@pytest.mark.parametrize("runtime,expected_attr", [("crewai", "Agent"), ("strands", "Agent")])
def test_agentic_mock_runtime_sets_runtime_entrypoints(
    agentic_mock_runtime: Callable[[str], dict[str, ModuleType]],
    runtime: str,
    expected_attr: str,
) -> None:
    """Runtime mocking fixture should install common runtime entrypoints."""
    modules = agentic_mock_runtime(runtime)

    assert hasattr(modules[runtime], expected_attr)


def test_agentic_fabric_agent_config_fixture(agentic_fabric_agent_config: dict[str, Any]) -> None:
    """Minimal fabric agent config should be usable by runtime tests."""
    assert agentic_fabric_agent_config["agents"]["tester"]["role"] == "Tester"
    assert agentic_fabric_agent_config["tasks"]["verify"]["agent"] == "tester"


def test_agentic_workspace_fixture(agentic_workspace: Path) -> None:
    """Workspace fixture should create a discoverable .fabric package."""
    manifest = agentic_workspace / "packages" / "sample" / ".fabric" / "manifest.yaml"
    agents = agentic_workspace / "packages" / "sample" / ".fabric" / "fabric_agents" / "test_fabric_agent" / "agents.yaml"
    tasks = agentic_workspace / "packages" / "sample" / ".fabric" / "fabric_agents" / "test_fabric_agent" / "tasks.yaml"

    assert manifest.exists()
    assert yaml.safe_load(manifest.read_text(encoding="utf-8"))["fabric_agents"]["test_fabric_agent"][
        "description"
    ] == "A test fabric agent"
    assert yaml.safe_load(agents.read_text(encoding="utf-8"))["tester"]["role"] == "Tester"
    assert yaml.safe_load(tasks.read_text(encoding="utf-8"))["verify"]["agent"] == "tester"


def test_agentic_workspace_fixture_uses_overridden_config(pytester: pytest.Pytester) -> None:
    """Workspace fixture should serialize overridden fabric agent configs."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makeconftest(
        """
        import pytest

        @pytest.fixture
        def agentic_fabric_agent_config():
            return {
                "name": "custom_agent",
                "description": "Custom description",
                "preferred_framework": "langgraph",
                "agents": {
                    "custom": {
                        "role": "Custom",
                        "goal": "Check override",
                        "backstory": "Fixture override",
                    },
                },
                "tasks": {
                    "custom_task": {
                        "description": "Use override",
                        "expected_output": "Override result",
                        "agent": "custom",
                    },
                },
            }
        """
    )
    pytester.makepyfile(
        """
        import yaml

        def test_workspace_uses_override(agentic_workspace):
            fabric_dir = agentic_workspace / "packages" / "sample" / ".fabric"
            manifest = yaml.safe_load((fabric_dir / "manifest.yaml").read_text(encoding="utf-8"))
            agent_config = manifest["fabric_agents"]["custom_agent"]
            agents = yaml.safe_load((fabric_dir / "fabric_agents" / "custom_agent" / "agents.yaml").read_text(encoding="utf-8"))
            tasks = yaml.safe_load((fabric_dir / "fabric_agents" / "custom_agent" / "tasks.yaml").read_text(encoding="utf-8"))

            assert agent_config["description"] == "Custom description"
            assert agent_config["preferred_framework"] == "langgraph"
            assert agents["custom"]["role"] == "Custom"
            assert tasks["custom_task"]["agent"] == "custom"
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(passed=1)


def test_agentic_e2e_marker_skips_by_default(pytester: pytest.Pytester) -> None:
    """Runtime-dependent tests should skip unless --agentic-e2e is passed."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.agentic_e2e
        def test_live_runtime():
            assert False
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(skipped=1)


def test_agentic_e2e_marker_runs_when_enabled(pytester: pytest.Pytester) -> None:
    """Runtime-dependent tests should run when --agentic-e2e is passed."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.agentic_e2e
        def test_live_runtime():
            assert True
        """
    )

    result = pytester.runpytest("-q", "--agentic-e2e")

    result.assert_outcomes(passed=1)
