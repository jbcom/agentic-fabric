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


def test_cmd_list_text_displays_framework_marked_fabric_agents(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package=None, framework=None, json=False)

    with patch.object(
        cli,
        "list_fabric_agents",
        return_value={"pkg": [{"name": "reviewer", "description": "reviews code", "required_framework": "crewai"}]},
    ):
        cli.cmd_list(args)

    output = capsys.readouterr().out
    assert "AVAILABLE FABRIC AGENTS" in output
    assert "pkg" in output
    assert "reviewer [crewai]: reviews code" in output


def test_cmd_list_json_flattens_packages(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", framework="langgraph", json=True)

    with patch.object(
        cli,
        "list_fabric_agents",
        return_value={"pkg": [{"name": "builder", "description": "builds", "required_framework": "langgraph"}]},
    ):
        cli.cmd_list(args)

    assert json.loads(capsys.readouterr().out) == {
        "fabric_agents": [
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
        fabric_agent="reviewer",
        file=None,
        input="review this",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.detect_framework", return_value="crewai"),
        patch("agentic_fabric.core.decomposer.run_fabric_agent_auto", return_value="done") as run_fabric_agent_auto,
    ):
        cli.cmd_run(args)

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["output"] == "done"
    assert data["framework_used"] == "crewai"
    run_fabric_agent_auto.assert_called_once_with(
        {"name": "reviewer"},
        inputs={"spec": "review this", "component_spec": "review this", "input": "review this"},
        framework="crewai",
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
        fabric_agent="reviewer",
        file=str(input_file),
        input=None,
        framework="strands",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".strands"}),
        patch.object(cli, "get_fabric_agent_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.run_fabric_agent_auto", return_value="done") as run_fabric_agent_auto,
    ):
        cli.cmd_run(args)

    data = json.loads(capsys.readouterr().out)
    assert data["success"] is True
    assert data["framework_used"] == "strands"
    assert run_fabric_agent_auto.call_args.kwargs["inputs"]["input"] == "from file"
    assert run_fabric_agent_auto.call_args.kwargs["framework"] == "strands"


def test_cmd_run_dispatches_single_agent_runner(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=False, runner="fake", package=None, fabric_agent=None)
    calls: list[tuple[SimpleNamespace, bool]] = []

    with patch.object(cli, "_cmd_run_single_agent", side_effect=lambda args, use_json, start_time: calls.append((args, use_json))):
        cli.cmd_run(args)

    assert calls == [(args, False)]
    assert capsys.readouterr().out == ""


def test_cmd_run_json_reports_missing_package(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(
        json=True,
        runner=None,
        package="missing",
        fabric_agent="reviewer",
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
        fabric_agent="reviewer",
        file=None,
        input="task",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", side_effect=ValueError("bad fabric agent")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_run(args)

    assert exc_info.value.code == 1
    assert json.loads(capsys.readouterr().out)["error"] == "bad fabric agent"


@pytest.mark.parametrize("use_json", [True, False])
def test_cmd_run_reports_file_read_errors(capsys: pytest.CaptureFixture[str], use_json: bool) -> None:
    """Multi-agent CLI runs should report unreadable input files."""
    args = SimpleNamespace(
        json=use_json,
        runner=None,
        package="pkg",
        fabric_agent="reviewer",
        file="/definitely/missing/task.txt",
        input=None,
        framework="auto",
    )

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(args)

    assert exc_info.value.code == 2
    output = capsys.readouterr().out
    if use_json:
        assert json.loads(output)["success"] is False
    else:
        assert "Error:" in output


def test_cmd_run_text_reports_missing_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=False, runner=None, package=None, fabric_agent=None)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(args)

    assert exc_info.value.code == 2
    assert "Package and fabric_agent are required" in capsys.readouterr().out


def test_cmd_run_json_reports_missing_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=True, runner=None, package=None, fabric_agent=None)

    with pytest.raises(SystemExit) as exc_info:
        cli.cmd_run(args)

    assert exc_info.value.code == 2
    assert json.loads(capsys.readouterr().out)["error"].startswith("Package and fabric_agent are required")


def test_cmd_run_text_reports_missing_package(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(
        json=False,
        runner=None,
        package="missing",
        fabric_agent="reviewer",
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
    output = capsys.readouterr().out
    assert "Package 'missing' not found" in output
    assert "known" in output


def test_cmd_run_text_uses_empty_input_and_requested_or_auto_framework(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    args = SimpleNamespace(
        json=False,
        runner=None,
        package="pkg",
        fabric_agent="reviewer",
        file=None,
        input=None,
        framework="langgraph",
    )
    calls: list[dict[str, Any]] = []

    def fake_run_fabric_agent_auto(fabric_agent_config: dict[str, Any], inputs: dict[str, str], framework: str | None = None) -> str:
        calls.append({"fabric_agent_config": fabric_agent_config, "inputs": inputs, "framework": framework})
        return "done"

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".fabric"}),
        patch.object(cli, "get_fabric_agent_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.run_fabric_agent_auto", side_effect=fake_run_fabric_agent_auto),
    ):
        cli.cmd_run(args)

    output = capsys.readouterr().out
    assert "Framework: langgraph (requested)" in output
    assert calls[0]["inputs"] == {"spec": "", "component_spec": "", "input": ""}
    assert calls[0]["framework"] == "langgraph"

    args.framework = "auto"
    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".fabric"}),
        patch.object(cli, "get_fabric_agent_config", return_value={"name": "reviewer"}),
        patch("agentic_fabric.core.decomposer.detect_framework", return_value="strands"),
        patch("agentic_fabric.core.decomposer.run_fabric_agent_auto", return_value="done"),
    ):
        cli.cmd_run(args)

    assert "Framework: strands (auto-detected)" in capsys.readouterr().out


def test_cmd_run_text_success_and_error_paths(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(
        json=False,
        runner=None,
        package="pkg",
        fabric_agent="reviewer",
        file=None,
        input="task",
        framework="auto",
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", return_value={"name": "reviewer", "required_framework": "crewai"}),
        patch("agentic_fabric.core.decomposer.run_fabric_agent_auto", return_value="done"),
    ):
        cli.cmd_run(args)

    output = capsys.readouterr().out
    assert "Running pkg/reviewer" in output
    assert "Framework: crewai" in output
    assert "done" in output

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", side_effect=RuntimeError("boom")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_run(args)

    assert exc_info.value.code == 1
    assert "Error: boom" in capsys.readouterr().out


def test_cmd_info_json_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", fabric_agent="reviewer", json=True)
    config = {
        "description": "Reviews code",
        "required_framework": "crewai",
        "agents": {"reviewer": {"role": "Code Reviewer"}},
        "tasks": {"review": {"description": "Review the change"}},
        "knowledge_paths": ["knowledge"],
    }

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", return_value=config),
    ):
        cli.cmd_info(args)

    data = json.loads(capsys.readouterr().out)
    assert data["package"] == "pkg"
    assert data["required_framework"] == "crewai"
    assert data["agents"] == [{"name": "reviewer", "role": "Code Reviewer"}]
    assert data["tasks"] == [{"name": "review", "description": "Review the change"}]


def test_cmd_info_json_reports_config_error(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", fabric_agent="missing", json=True)

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", side_effect=ValueError("missing fabric agent")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_info(args)

    assert exc_info.value.code == 2
    assert json.loads(capsys.readouterr().out) == {"error": "missing fabric agent"}


def test_cmd_info_json_reports_missing_package(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="missing", fabric_agent="reviewer", json=True)

    with (
        patch.object(cli, "discover_packages", return_value={"known": Path(".crewai")}),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_info(args)

    assert exc_info.value.code == 2
    data = json.loads(capsys.readouterr().out)
    assert data["error"] == "Package 'missing' not found"
    assert data["available_packages"] == ["known"]


def test_cmd_info_text_success_and_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(package="pkg", fabric_agent="reviewer", json=False)
    config = {
        "description": "Reviews code",
        "agents": {"reviewer": {"role": "Code Reviewer"}},
        "tasks": {"review": {"description": "Review the change in detail"}},
        "knowledge_paths": [tmp_path / "knowledge"],
    }

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", return_value=config),
    ):
        cli.cmd_info(args)

    output = capsys.readouterr().out
    assert "FABRIC AGENT: pkg/reviewer" in output
    assert "Code Reviewer" in output
    assert "Review the change" in output

    with (
        patch.object(cli, "discover_packages", return_value={}),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_info(args)

    assert exc_info.value.code == 2
    assert "Package 'pkg' not found" in capsys.readouterr().out

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": tmp_path / ".crewai"}),
        patch.object(cli, "get_fabric_agent_config", side_effect=ValueError("missing fabric agent")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_info(args)

    assert exc_info.value.code == 2
    assert "missing fabric agent" in capsys.readouterr().out


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


def test_cmd_list_runners_text_lists_available_unavailable_and_bad_profiles(
    capsys: pytest.CaptureFixture[str],
) -> None:
    good_runner = FakeCliRunner(available=True)
    bad_runner = FakeCliRunner(available=False)

    def fake_get_cli_runner(profile: str) -> FakeCliRunner:
        if profile == "broken":
            raise RuntimeError("broken profile")
        return good_runner if profile == "good" else bad_runner

    with (
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", return_value=["good", "bad", "broken"]),
        patch("agentic_fabric.core.decomposer.get_cli_runner", side_effect=fake_get_cli_runner),
    ):
        cli.cmd_list_runners(SimpleNamespace(json=False))

    captured = capsys.readouterr()
    assert "AVAILABLE SINGLE-AGENT CLI RUNNERS" in captured.out
    assert "good: Runs fake tasks" in captured.out
    assert "bad: Runs fake tasks" in captured.out
    assert "Install: install fake" in captured.out
    assert "Requires: FAKE_API_KEY" in captured.out
    assert "Warning: Could not load profile 'broken'" in captured.err


def test_cmd_list_runners_text_reports_missing_profiles(capsys: pytest.CaptureFixture[str]) -> None:
    with (
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", side_effect=FileNotFoundError("no profiles")),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli.cmd_list_runners(SimpleNamespace(json=False))

    assert exc_info.value.code == 2
    assert "Error: no profiles" in capsys.readouterr().out


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


def test_single_agent_text_requires_input(capsys: pytest.CaptureFixture[str]) -> None:
    args = SimpleNamespace(json=False, runner="fake", input=None, file=None, package=None)

    with pytest.raises(SystemExit) as exc_info:
        cli._cmd_run_single_agent(args, use_json=False, start_time=0)

    assert exc_info.value.code == 2
    assert "No input provided" in capsys.readouterr().out


@pytest.mark.parametrize("use_json", [True, False])
def test_single_agent_reports_file_read_errors(capsys: pytest.CaptureFixture[str], use_json: bool) -> None:
    """Single-agent CLI runs should report unreadable input files."""
    args = SimpleNamespace(
        json=use_json,
        runner="fake",
        input=None,
        file="/definitely/missing/task.txt",
        package=None,
    )

    with pytest.raises(SystemExit) as exc_info:
        cli._cmd_run_single_agent(args, use_json=use_json, start_time=0)

    assert exc_info.value.code == 2
    output = capsys.readouterr().out
    if use_json:
        assert json.loads(output)["success"] is False
    else:
        assert "Error:" in output


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


def test_single_agent_text_success_unavailable_and_error_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    input_file = tmp_path / "task.txt"
    input_file.write_text("from file", encoding="utf-8")
    package_dir = tmp_path / "pkg" / ".fabric"
    fake_runner = FakeCliRunner(result="fixed")
    args = SimpleNamespace(
        json=False,
        runner="fake",
        input=None,
        file=str(input_file),
        package="pkg",
        model=None,
        auto_approve=True,
    )

    with (
        patch.object(cli, "discover_packages", return_value={"pkg": package_dir}),
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=fake_runner),
    ):
        cli._cmd_run_single_agent(args, use_json=False, start_time=0)

    output = capsys.readouterr().out
    assert "Running single-agent: fake" in output
    assert "Runner: Fake Runner" in output
    assert "fixed" in output
    assert fake_runner.calls[0]["task"] == "from file"

    unavailable_runner = FakeCliRunner(available=False)
    args.input = "task"
    args.file = None
    with (
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=unavailable_runner),
        patch("agentic_fabric.core.decomposer.get_available_cli_runners", return_value=["other"]),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli._cmd_run_single_agent(args, use_json=False, start_time=0)

    assert exc_info.value.code == 2
    assert "Runner 'fake' not available" in capsys.readouterr().out

    def broken_run(**kwargs: Any) -> str:
        raise FileNotFoundError("missing binary")

    fake_runner.run = broken_run
    with (
        patch("agentic_fabric.core.decomposer.get_cli_runner", return_value=fake_runner),
        pytest.raises(SystemExit) as exc_info,
    ):
        cli._cmd_run_single_agent(args, use_json=False, start_time=0)

    assert exc_info.value.code == 1
    assert "missing binary" in capsys.readouterr().out


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
