"""Pytest plugin fixtures for agentic-fabric projects."""

from __future__ import annotations

from collections.abc import Callable
from importlib.util import find_spec
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml


RUNTIME_MODULES: dict[str, tuple[str, ...]] = {
    "crewai": (
        "crewai",
        "crewai.knowledge",
        "crewai.knowledge.source",
        "crewai.knowledge.source.text_file_knowledge_source",
    ),
    "langgraph": ("langgraph", "langgraph.prebuilt", "langchain_anthropic"),
    "strands": ("strands",),
}


def pytest_addoption(parser: pytest.Parser) -> None:
    """Register agentic-fabric test options."""
    parser.addoption(
        "--agentic-e2e",
        action="store_true",
        default=False,
        help="Run agentic-fabric tests that require external runtime dependencies.",
    )


def pytest_configure(config: pytest.Config) -> None:
    """Register agentic-fabric markers."""
    config.addinivalue_line(
        "markers",
        "agentic_e2e: tests that require real agent runtimes, credentials, or external services",
    )
    config.addinivalue_line(
        "markers",
        "agentic_runtime(runtime): tests that require one optional agent runtime",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip live runtime tests unless explicitly enabled."""
    if config.getoption("--agentic-e2e"):
        return

    skip_runtime = pytest.mark.skip(reason="agentic runtime test disabled; pass --agentic-e2e to run")
    for item in items:
        if "agentic_e2e" in item.keywords or "agentic_runtime" in item.keywords:
            item.add_marker(skip_runtime)


@pytest.fixture
def agentic_runtime_available() -> Callable[[str], bool]:
    """Return a predicate that checks whether an optional runtime can import."""

    def check(module_name: str) -> bool:
        return find_spec(module_name) is not None

    return check


@pytest.fixture
def agentic_runtime_registry() -> dict[str, Any]:
    """Return a mutable runtime registry for tests."""
    return {}


@pytest.fixture
def agentic_runtime_modules() -> dict[str, tuple[str, ...]]:
    """Return known import modules for optional runtimes."""
    return dict(RUNTIME_MODULES)


@pytest.fixture
def agentic_mock_runtime(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], dict[str, ModuleType]]:
    """Return a helper that installs fake runtime modules into ``sys.modules``."""

    def install(runtime: str) -> dict[str, ModuleType]:
        import sys

        modules: dict[str, ModuleType] = {}
        for module_name in RUNTIME_MODULES[runtime]:
            module = ModuleType(module_name)
            modules[module_name] = module
            monkeypatch.setitem(sys.modules, module_name, module)
            parent_name, separator, child_name = module_name.rpartition(".")
            if separator and parent_name in sys.modules:
                setattr(sys.modules[parent_name], child_name, module)

        if "crewai" in modules:
            modules["crewai"].__dict__.update({"Agent": object, "Crew": object, "Task": object})
        if "langgraph.prebuilt" in modules:
            modules["langgraph.prebuilt"].__dict__["create_react_agent"] = (
                lambda *args, **kwargs: {"args": args, "kwargs": kwargs}
            )
        if "strands" in modules:
            modules["strands"].__dict__["Agent"] = object
        return modules

    return install


@pytest.fixture
def agentic_fabric_agent_config() -> dict[str, Any]:
    """Return a minimal framework-neutral fabric agent config."""
    return {
        "name": "test_fabric_agent",
        "description": "A test fabric agent",
        "agents": {
            "tester": {
                "role": "Tester",
                "goal": "Verify behavior",
                "backstory": "Careful runtime test agent.",
            }
        },
        "tasks": {
            "verify": {
                "description": "Verify the requested behavior.",
                "expected_output": "A concise result",
                "agent": "tester",
            }
        },
        "knowledge_paths": [],
    }


@pytest.fixture
def agentic_workspace(tmp_path: Path, agentic_fabric_agent_config: dict[str, Any]) -> Path:
    """Create a minimal workspace with a ``.fabric`` package."""
    workspace = tmp_path / "workspace"
    fabric_dir = workspace / "packages" / "sample" / ".fabric"
    fabric_agent_name = str(agentic_fabric_agent_config.get("name", "test_fabric_agent"))
    config_dir = fabric_dir / "fabric_agents" / fabric_agent_name
    config_dir.mkdir(parents=True)
    manifest_agent_config: dict[str, Any] = {
        "description": agentic_fabric_agent_config.get("description", ""),
        "agents": f"fabric_agents/{fabric_agent_name}/agents.yaml",
        "tasks": f"fabric_agents/{fabric_agent_name}/tasks.yaml",
    }
    if "preferred_framework" in agentic_fabric_agent_config:
        manifest_agent_config["preferred_framework"] = agentic_fabric_agent_config["preferred_framework"]

    manifest = {
        "name": "sample",
        "description": "Test package",
        "fabric_agents": {fabric_agent_name: manifest_agent_config},
    }
    fabric_dir.joinpath("manifest.yaml").write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    config_dir.joinpath("agents.yaml").write_text(
        yaml.safe_dump(agentic_fabric_agent_config.get("agents", {}), sort_keys=False),
        encoding="utf-8",
    )
    config_dir.joinpath("tasks.yaml").write_text(
        yaml.safe_dump(agentic_fabric_agent_config.get("tasks", {}), sort_keys=False),
        encoding="utf-8",
    )
    return workspace
