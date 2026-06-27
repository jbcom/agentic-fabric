"""Tests for the legacy CrewAI runner facade."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from agentic_fabric.core import runner as crew_runner


class FakeRawResult:
    """Result object exposing CrewAI's raw output attribute."""

    raw = "raw output"


class FakeStringResult:
    """Result object that relies on string conversion."""

    def __str__(self) -> str:
        return "string output"


class FakeCrew:
    """Minimal crew object with kickoff capture."""

    def __init__(self, result: Any) -> None:
        self.result = result
        self.inputs: dict[str, Any] | None = None

    def kickoff(self, inputs: dict[str, Any]) -> Any:
        self.inputs = inputs
        return self.result


def test_run_crew_discovers_package_loads_config_and_returns_raw(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    crewai_dir = tmp_path / "pkg" / ".crewai"
    fake_crew = FakeCrew(FakeRawResult())
    calls: list[tuple[Any, ...]] = []

    monkeypatch.setattr(crew_runner, "discover_packages", lambda workspace_root: {"pkg": crewai_dir})

    def fake_get_crew_config(path: Path, crew_name: str) -> dict[str, Any]:
        calls.append(("config", path, crew_name))
        return {"name": crew_name}

    def fake_load_crew_from_config(config: dict[str, Any]) -> FakeCrew:
        calls.append(("load", config))
        return fake_crew

    monkeypatch.setattr(crew_runner, "get_crew_config", fake_get_crew_config)
    monkeypatch.setattr(crew_runner, "load_crew_from_config", fake_load_crew_from_config)

    result = crew_runner.run_crew("pkg", "builder", inputs={"topic": "tests"}, workspace_root=tmp_path)

    assert result == "raw output"
    assert fake_crew.inputs == {"topic": "tests"}
    assert calls == [("config", crewai_dir, "builder"), ("load", {"name": "builder"})]


def test_run_crew_reports_available_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(crew_runner, "discover_packages", lambda workspace_root: {"known": Path(".crewai")})

    with pytest.raises(ValueError, match=r"Package 'missing' not found. Available: \['known'\]"):
        crew_runner.run_crew("missing", "builder")


def test_run_crew_defaults_inputs_to_empty_dict(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_crew = FakeCrew(FakeStringResult())

    monkeypatch.setattr(crew_runner, "discover_packages", lambda workspace_root: {"pkg": tmp_path})
    monkeypatch.setattr(crew_runner, "get_crew_config", lambda path, crew_name: {"name": crew_name})
    monkeypatch.setattr(crew_runner, "load_crew_from_config", lambda config: fake_crew)

    result = crew_runner.run_crew("pkg", "builder")

    assert result == "string output"
    assert fake_crew.inputs == {}


def test_run_crew_from_path_loads_direct_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_crew = FakeCrew(FakeStringResult())

    monkeypatch.setattr(crew_runner, "get_crew_config", lambda path, crew_name: {"path": path, "name": crew_name})
    monkeypatch.setattr(crew_runner, "load_crew_from_config", lambda config: fake_crew)

    result = crew_runner.run_crew_from_path(tmp_path / ".crewai", "builder", inputs={"x": 1})

    assert result == "string output"
    assert fake_crew.inputs == {"x": 1}
