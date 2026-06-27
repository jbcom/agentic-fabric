"""Inspect AgenticData runtime context without requiring optional frameworks."""

from __future__ import annotations

import json

from typing import Any

from agentic_fabric import AgenticData, get_framework_info


def inspect_runtime_context() -> dict[str, Any]:
    """Return a serializable summary of runtime context behavior."""
    data = AgenticData({"task": "review"})
    data.register_agent("reviewer", {"name": "reviewer", "agents": {}, "tasks": {}})
    data.use_runtime("crewai", strict=False)

    return {
        "active_runtime": data.active_runtime,
        "registered_agents": sorted(data.agent_registry),
        "runtime_names": [item["name"] for item in get_framework_info()],
        "vendor_fabric_available": data.vendor_fabric_available,
    }


if __name__ == "__main__":
    print(json.dumps(inspect_runtime_context(), indent=2))
