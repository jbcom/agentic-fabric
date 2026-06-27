"""Discover and inspect a framework-agnostic crew workspace."""

from __future__ import annotations

import json

from pathlib import Path
from typing import Any

from agentic_fabric.core.discovery import discover_packages, get_crew_config, load_manifest


DEFAULT_WORKSPACE = Path(__file__).parent / "sample_workspace"


def summarize_workspace(workspace_root: Path = DEFAULT_WORKSPACE) -> dict[str, Any]:
    """Return a deterministic summary of crews in a workspace."""
    packages = discover_packages(workspace_root=workspace_root)
    summary: dict[str, Any] = {"workspace": str(workspace_root), "packages": {}}

    for package_name, config_dir in sorted(packages.items()):
        manifest = load_manifest(config_dir)
        crew_summaries = {}
        for crew_name in sorted(manifest.get("crews", {})):
            crew_config = get_crew_config(config_dir, crew_name)
            crew_summaries[crew_name] = {
                "description": crew_config.get("description", ""),
                "required_framework": crew_config.get("required_framework"),
                "agents": sorted(crew_config.get("agents", {})),
                "tasks": sorted(crew_config.get("tasks", {})),
            }

        summary["packages"][package_name] = {
            "config_dir": config_dir.name,
            "crews": crew_summaries,
        }

    return summary


def main() -> None:
    """Print the sample workspace summary as JSON."""
    print(json.dumps(summarize_workspace(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
