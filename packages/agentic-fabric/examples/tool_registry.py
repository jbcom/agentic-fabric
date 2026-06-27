"""Resolve tools without importing optional framework packages."""

from __future__ import annotations

import json

from typing import Any

from agentic_fabric.tools.registry import resolve_tool


def inspect_registry() -> dict[str, Any]:
    """Return deterministic registry resolution examples."""
    framework_dirs = resolve_tool("agentic_fabric.core.discovery:FRAMEWORK_DIRS")
    unresolved_mcp = resolve_tool("mcp://git/execute_command")

    return {
        "framework_dirs": framework_dirs,
        "mcp_git_available": unresolved_mcp is not None,
    }


def main() -> None:
    """Print registry inspection as JSON."""
    print(json.dumps(inspect_registry(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
