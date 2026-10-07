"""Tests for repository workflow contracts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


WORKSPACE_ROOT = Path(__file__).resolve().parents[3]


def load_workflow(name: str) -> dict[str, Any]:
    """Load a GitHub Actions workflow without YAML 1.1 boolean coercion issues."""
    return yaml.safe_load((WORKSPACE_ROOT / ".github" / "workflows" / name).read_text(encoding="utf-8"))


def test_automerge_uses_base_context_and_merge_commits() -> None:
    """Automerge should use only trusted metadata and preserve commit history."""
    workflow = load_workflow("automerge.yml")
    automerge = workflow["jobs"]["automerge"]
    steps = automerge["steps"]

    assert workflow[True] == {
        "pull_request_target": {"types": ["opened", "reopened", "synchronize", "ready_for_review"]}
    }
    assert workflow["permissions"] == {"contents": "write", "pull-requests": "write"}
    assert "github-actions[bot]" in automerge["if"]
    assert "minor-and-patch" in automerge["if"]
    assert all("uses" not in step or "actions/checkout" not in step["uses"] for step in steps)
    assert steps == [
        {
            "name": "Enable auto-merge (merge commit)",
            "env": {
                "GH_TOKEN": "${{ secrets.CI_GITHUB_TOKEN }}",
                "PR_URL": "${{ github.event.pull_request.html_url }}",
            },
            "run": 'gh pr merge --auto --merge "$PR_URL"',
        }
    ]


def test_ci_and_cd_quality_run_security_audit_and_examples() -> None:
    """CI and CD quality gates should include auditing and shipped examples."""
    for workflow_name in ("ci.yml", "cd.yml"):
        workflow = load_workflow(workflow_name)
        quality_steps = workflow["jobs"]["quality"]["steps"]
        tox_commands = [step["run"] for step in quality_steps if step.get("run", "").startswith("tox -e ")]

        assert tox_commands == ["tox -e lint,typecheck,audit,examples,coverage,plugin,docs,build"]


def test_ci_has_a_sourcey_aware_machine_gate_and_fork_policy() -> None:
    """CI should validate Sourcey and reject fork-controlled deployment inputs."""
    workflow = load_workflow("ci.yml")

    assert workflow["jobs"]["quality"]["name"] == "Quality, Sourcey docs, build"
    assert any("actions/setup-node@" in step.get("uses", "") for step in workflow["jobs"]["quality"]["steps"])
    assert workflow["jobs"]["dependency-review"]["name"] == "Dependency Review / gate"
    assert workflow["jobs"]["repository-policy"]["name"] == "Repository Policy / gate"
    assert workflow["jobs"]["gate"]["name"] == "CI / gate"
    assert "release-please--" in workflow["jobs"]["test"]["if"]
    assert "minor-and-patch" in workflow["jobs"]["quality"]["if"]
    policy_script = workflow["jobs"]["repository-policy"]["steps"][0]["with"]["script"]
    assert "pull.head.repo.full_name" in policy_script
    assert "docs/sourcey.config.ts" in policy_script


def test_sourcey_is_the_only_documentation_renderer() -> None:
    """Sourcey config, generated API reference, and legacy Sphinx removal stay aligned."""
    docs = WORKSPACE_ROOT / "docs"

    assert (docs / "sourcey.config.ts").is_file()
    assert (docs / "package-lock.json").is_file()
    assert (docs / "api-reference.md").is_file()
    assert not (docs / "conf.py").exists()
    assert not any(docs.glob("*.rst"))
    assert "sourcey" in (docs / "package.json").read_text(encoding="utf-8")
