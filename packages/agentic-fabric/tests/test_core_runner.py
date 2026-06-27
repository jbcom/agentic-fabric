"""Tests for the direct fabric-agent runner facade.

The runner routes through the framework-agnostic decomposer
(run_fabric_agent_auto) so that required_framework from framework-specific
config directories is honored.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agentic_fabric.core import runner as fabric_runner


class FakeRunner:
    """Minimal runner-like object that returns a string."""

    def __init__(self, output: str) -> None:
        self._output = output

    def build_fabric_agent(self, config: dict[str, Any]) -> Any:
        return config

    def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
        self._inputs = inputs
        return self._output


def test_run_fabric_agent_discovers_package_loads_config_and_returns_result(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_dir = tmp_path / "pkg" / ".fabric"
    calls: list[tuple[Any, ...]] = []

    monkeypatch.setattr(fabric_runner, "discover_packages", lambda workspace_root: {"pkg": config_dir})

    def fake_get_fabric_agent_config(path: Path, fabric_agent_name: str) -> dict[str, Any]:
        calls.append(("config", path, fabric_agent_name))
        return {"name": fabric_agent_name}

    def fake_run_fabric_agent_auto(config: dict[str, Any], inputs: dict[str, Any] | None = None) -> str:
        calls.append(("run", config, inputs))
        return "raw output"

    monkeypatch.setattr(fabric_runner, "get_fabric_agent_config", fake_get_fabric_agent_config)
    monkeypatch.setattr(fabric_runner, "run_fabric_agent_auto", fake_run_fabric_agent_auto)

    result = fabric_runner.run_fabric_agent("pkg", "builder", inputs={"topic": "tests"}, workspace_root=tmp_path)

    assert result == "raw output"
    assert calls == [
        ("config", config_dir, "builder"),
        ("run", {"name": "builder"}, {"topic": "tests"}),
    ]


def test_run_fabric_agent_reports_available_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(fabric_runner, "discover_packages", lambda workspace_root: {"known": Path(".fabric")})

    with pytest.raises(ValueError, match=r"Package 'missing' not found. Available: \['known'\]"):
        fabric_runner.run_fabric_agent("missing", "builder")


def test_run_fabric_agent_defaults_inputs_to_empty_dict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Any, ...]] = []

    monkeypatch.setattr(fabric_runner, "discover_packages", lambda workspace_root: {"pkg": tmp_path})
    monkeypatch.setattr(fabric_runner, "get_fabric_agent_config", lambda path, fabric_agent_name: {"name": fabric_agent_name})

    def fake_run_fabric_agent_auto(config: dict[str, Any], inputs: dict[str, Any] | None = None) -> str:
        calls.append(("run", config, inputs))
        return "string output"

    monkeypatch.setattr(fabric_runner, "run_fabric_agent_auto", fake_run_fabric_agent_auto)

    result = fabric_runner.run_fabric_agent("pkg", "builder")

    assert result == "string output"
    assert calls == [("run", {"name": "builder"}, {})]


def test_run_fabric_agent_from_path_loads_direct_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Any, ...]] = []

    monkeypatch.setattr(
        fabric_runner,
        "get_fabric_agent_config",
        lambda path, fabric_agent_name: {"path": path, "name": fabric_agent_name},
    )

    def fake_run_fabric_agent_auto(config: dict[str, Any], inputs: dict[str, Any] | None = None) -> str:
        calls.append(("run", config, inputs))
        return "string output"

    monkeypatch.setattr(fabric_runner, "run_fabric_agent_auto", fake_run_fabric_agent_auto)

    result = fabric_runner.run_fabric_agent_from_path(tmp_path / ".fabric", "builder", inputs={"x": 1})

    assert result == "string output"
    assert calls == [("run", {"path": tmp_path / ".fabric", "name": "builder"}, {"x": 1})]
