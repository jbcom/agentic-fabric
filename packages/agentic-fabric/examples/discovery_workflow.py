"""Discover and inspect a framework-agnostic fabric workspace."""

from __future__ import annotations

import json
import sys

from pathlib import Path
from typing import Any

from agentic_fabric.core.discovery import discover_packages, get_fabric_agent_config, load_manifest


DEFAULT_WORKSPACE = Path(__file__).parent / "sample_workspace"


def summarize_workspace(workspace_root: Path = DEFAULT_WORKSPACE) -> dict[str, Any]:
    """Return a deterministic summary of fabric agents in a workspace."""
    packages = discover_packages(workspace_root=workspace_root)
    summary: dict[str, Any] = {"workspace": str(workspace_root), "packages": {}}

    for package_name, config_dir in sorted(packages.items()):
        manifest = load_manifest(config_dir)
        fabric_agent_summaries = {}
        for fabric_agent_name in sorted(manifest.get("fabric_agents", {})):
            fabric_agent_config = get_fabric_agent_config(config_dir, fabric_agent_name)
            fabric_agent_summaries[fabric_agent_name] = {
                "description": fabric_agent_config.get("description", ""),
                "required_framework": fabric_agent_config.get("required_framework"),
                "agents": sorted(fabric_agent_config.get("agents", {})),
                "tasks": sorted(fabric_agent_config.get("tasks", {})),
            }

        summary["packages"][package_name] = {
            "config_dir": config_dir.name,
            "fabric_agents": fabric_agent_summaries,
        }

    return summary


def main() -> None:
    """Print the sample workspace summary as JSON."""
    sys.stdout.write(json.dumps(summarize_workspace(), indent=2, sort_keys=True))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
