"""Tests for repository workflow contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def load_workflow(name: str) -> dict[str, Any]:
    """Load a GitHub Actions workflow without YAML 1.1 boolean coercion issues."""
    return yaml.safe_load((WORKSPACE_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_automerge_uses_base_context_without_checkout_or_secrets() -> None:
    """Automerge should match the split-package base-context workflow contract."""
    workflow = load_workflow("automerge.yml")
    automerge = workflow["jobs"]["automerge"]
    steps = automerge["steps"]

    assert workflow[True] == {
        "pull_request_target": {"types": ["opened", "reopened", "synchronize", "ready_for_review"]}
    }
    assert workflow["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert "github-actions[bot]" in automerge["if"]
    assert all("uses" not in step or "actions/checkout" not in step["uses"] for step in steps)
    assert steps == [
        {
            "name": "Enable auto-merge (squash)",
            "env": {
                "GH_TOKEN": "${{ github.token }}",
                "PR_URL": "${{ github.event.pull_request.html_url }}",
            },
            "run": 'gh pr merge --auto --squash "$PR_URL"',
        }
    ]


def test_ci_and_cd_quality_run_security_audit_and_examples() -> None:
    """CI and CD quality gates should include auditing and shipped examples."""
    for workflow_name in ("ci.yml", "cd.yml"):
        workflow = load_workflow(workflow_name)
        quality_steps = workflow["jobs"]["quality"]["steps"]
        tox_commands = [step["run"] for step in quality_steps if step.get("run", "").startswith("tox -e ")]

        assert tox_commands == ["tox -e lint,typecheck,audit,examples,coverage,plugin,docs,build"]
