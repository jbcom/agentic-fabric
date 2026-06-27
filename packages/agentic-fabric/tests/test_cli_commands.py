"""Focused tests for CLI command helpers."""

from __future__ import annotations

import json

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

from agentic_fabric import main as cli


class FakeCliRunner:
    """Small CLI runner stand-in used by command tests."""

    def __init__(self, *, available: bool = True, result: str = "runner output") -> None:
        self.config = SimpleNamespace(
            name="Fake Runner",
            description="Runs fake tasks",
            install_cmd="install fake",
            docs_url="https://example.com/fake",
        )
        self.available = available
        self.result = result
        self.calls: list[dict[str, Any]] = []

    def is_available(self) -> bool:
        return self.available

    def get_required_env_vars(self) -> list[str]:
        return ["FAKE_API_KEY"]

    def run(self, **kwargs: Any) -> str:
        self.calls.append(kwargs)
        return self.result


def test_cmd_list_text_displays_framework_marked_crews(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package=None, framework=None, json=False)

    with patch.object(
        cli,
        "list_crews",
        return_value={"pkg": [{"name": "reviewer", "description": "reviews code", "required_framework": "crewai"}]},
    ):
        cli.cmd_list(args)

    output = capsys.readouterr().out
    assert "AVAILABLE CREWS" in output
    assert "pkg" in output
    assert "reviewer [crewai]: reviews code" in output


def test_cmd_list_json_flattens_packages(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", framework="langgraph", json=True)

    with patch.object(
        cli,
        "list_crews",
        return_value={"pkg": [{"name": "builder", "description": "builds", "required_framework": "langgraph"}]},
    ):
        cli.cmd_list(args)

    assert json.loads(capsys.readouterr().out) == {
        "crews": [
            {
                "package": "pkg",
                "name": "builder",
                "description": "builds",
                "required_framework": "langgraph",
            }
        ]
    }


def test_cmd_run_json_success_auto_detects_framework(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = SimpleNamespace(
        json=True,
        runner=None,
        package="pkg",
        crew="reviewer",
        file=None,
        input="review this",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_crew_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.detect_framework", return_value="crewai"),
        patch("agentic_fabric.core.decomposer.run_crew_auto", return_value="done") as run_crew_auto,
    ):
        cli.cmd_run(args)

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["output"] == "done"
    assert data["framework_used"] == "crewai"
    run_crew_auto.assert_called_once_with(
        {"name": "reviewer"},
        inputs={"spec": "review this", "component_spec": "review this", "input": "review this"},
        framework=None,
    )


def test_cmd_run_json_uses_file_input_and_requested_framework(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = tmp_path / "task.txt"
    input_file.write_text("from file", encoding="utf-8")
    args = SimpleNamespace(
        json=True,
        runner=None,
        package="pkg",
        crew="reviewer",
        file=str(input_file),
        input=None,
        framework="strands",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".strands"}),
        patch.object(cli, "get_crew_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.run_crew_auto", return_value="done") as run_crew_auto,
    ):
        cli.cmd_run(args)

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["framework_used"] == "strands"
    assert run_crew_auto.call_args.kwargs["inputs"]["input"] == "from file"
    assert run_crew_auto.call_args.kwargs["framework"] == "strands"


def test_cmd_run_json_reports_missing_package(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(
        json=True,
        runner=None,
        package="missing",
        crew="reviewer",
        file=None,
        input="task",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"known": Path(".crewai")}),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_run(args)

    assert exc_info.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["success"] is False
    assert data["available_packages"] == ["known"]


def test_cmd_run_json_reports_execution_errors(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = SimpleNamespace(
        json=True,
        runner=None,
        package="pkg",
        crew="reviewer",
        file=None,
        input="task",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_crew_config", side_effect=ValueError("bad crew")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_run(args)

    assert exc_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["error"] == "bad crew"


def test_cmd_info_json_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", crew="reviewer", json=True)
    config = {
        "description": "Reviews code",
        "required_framework": "crewai",
        "agents": {"reviewer": {"role": "Code Reviewer"}},
        "tasks": {"review": {"description": "Review the change"}},
        "knowledge_paths": ["knowledge"],
    }

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_crew_config", return_value=config),
    ):
        cli.cmd_info(args)

    data = json.loads(capsys.readouterr().out)
    assert data["package"] == "pkg"
    assert data["required_framework"] == "crewai"
    assert data["agents"] == [{"name": "reviewer", "role": "Code Reviewer"}]
    assert data["tasks"] == [{"name": "review", "description": "Review the change"}]


def test_cmd_info_json_reports_config_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", crew="missing", json=True)

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_crew_config", side_effect=ValueError("missing crew")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_info(args)

    assert exc_info.value.code == 2
    assert json.loads(capsys.readouterr().out) == {"error": "missing crew"}


def test_cmd_list_runners_json_skips_bad_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    fake_runner = FakeCliRunner()

    def fake_get_cli_runner(profile: str) -> FakeCliRunner:
        if profile == "bad":
            raise RuntimeError("broken")
        return fake_runner

    with (
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", return_value=["good", "bad"]),
        patch("agentic_fabric.core.decomposer.get_cli_runner", side_effect=fake_get_cli_runner),
    ):
        cli.cmd_list_runners(SimpleNamespace(json=True))

    data = json.loads(capsys.readouterr().out)
    assert data["runners"][0]["name"] == "good"
    assert data["runners"][0]["available"] is True
    assert data["runners"][0]["required_env"] == ["FAKE_API_KEY"]


def test_cmd_list_runners_reports_missing_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", side_effect=FileNotFoundError("no profiles")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_list_runners(SimpleNamespace(json=True))

    assert exc_info.value.code == 2
    assert json.loads(capsys.readouterr().out) == {"error": "no profiles"}


def test_single_agent_json_success_uses_package_workdir(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    fake_runner = FakeCliRunner(result="fixed")
    package_dir = tmp_path / "pkg" / ".crewai"

    args = SimpleNamespace(
        json=True,
        runner="fake",
        input="fix it",
        file=None,
        package="pkg",
        model="small",
        auto_approve=False,
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": package_dir}),
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=fake_runner),
    ):
        cli._cmd_run_single_agent(args, use_json=True, start_time=0)

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["output"] == "fixed"
    assert fake_runner.calls == [
        {
            "task": "fix it",
            "working_dir": str(package_dir.parent),
            "auto_approve": False,
        }
    ]


def test_single_agent_json_requires_input(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=True, runner="fake", input=None, file=None, package=None)

    with pytest.raises(SystemExit) as exc_info:
        cli._cmd_run_single_agent(args, use_json=True, start_time=0)

    assert exc_info.value.code == 2
    assert json.loads(capsys.readouterr().out)["error"] == "No input provided. Use --input or --file"


def test_single_agent_json_reports_unavailable_runner(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=True, runner="fake", input="task", file=None, package=None, model=None)
    fake_runner = FakeCliRunner(available=False)

    with (
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=fake_runner),
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", return_value=["other"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli._cmd_run_single_agent(args, use_json=True, start_time=0)

    assert exc_info.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["success"] is False
    assert data["available_runners"] == ["other"]


def test_single_agent_json_reports_runner_errors(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=True, runner="fake", input="task", file=None, package=None, model=None)
    fake_runner = FakeCliRunner()

    def broken_run(**kwargs: Any) -> str:
        raise RuntimeError("runner failed")

    fake_runner.run = broken_run

    with (
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=fake_runner),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli._cmd_run_single_agent(args, use_json=True, start_time=0)

    assert exc_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["error"] == "runner failed"
