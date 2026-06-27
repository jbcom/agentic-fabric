"""Integration checks for shipped examples."""

from __future__ import annotations

import json
import subprocess
import sys

from pathlib import Path

from examples.discovery_workflow import DEFAULT_WORKSPACE, summarize_workspace
from examples.runtime_context import inspect_runtime_context
from examples.tool_registry import inspect_registry


ROOT = Path(__file__).resolve().parents[1]


def test_discovery_workflow_summary_uses_bundled_workspace() -> None:
    summary = summarize_workspace(DEFAULT_WORKSPACE)

    assert sorted(summary["packages"]) == ["review"]
    review = summary["packages"]["review"]
    assert review["config_dir"] == ".fabric"
    fabric_agent = review["fabric_agents"]["implementation_review"]
    assert fabric_agent["required_framework"] is None
    assert fabric_agent["agents"] == ["documenter", "reviewer"]
    assert fabric_agent["tasks"] == ["review_code", "review_docs"]


def test_tool_registry_example_inspects_core_registry() -> None:
    summary = inspect_registry()

    assert summary["framework_dirs"] == [".fabric", ".crewai", ".langgraph", ".strands"]
    assert summary["mcp_git_available"] is False


def test_runtime_context_example_inspects_agentic_data() -> None:
    summary = inspect_runtime_context()

    assert summary["active_runtime"] == "crewai"
    assert summary["registered_fabric_agents"] == ["reviewer"]
    assert summary["runtime_names"] == ["crewai", "langgraph", "strands"]


def test_discovery_workflow_script_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "discovery_workflow.py")],
        check=True,
        capture_output=True,
        text=True,
    )

    parsed = json.loads(result.stdout)
    assert "review" in parsed["packages"]


def test_tool_registry_script_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "tool_registry.py")],
        check=True,
        capture_output=True,
        text=True,
    )

    parsed = json.loads(result.stdout)
    assert parsed["mcp_git_available"] is False


def test_runtime_context_script_outputs_json() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "examples" / "runtime_context.py")],
        check=True,
        capture_output=True,
        text=True,
    )

    parsed = json.loads(result.stdout)
    assert parsed["active_runtime"] == "crewai"
