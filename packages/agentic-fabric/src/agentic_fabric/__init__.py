"""agentic-fabric: Framework-agnostic AI fabric orchestration.

Declare fabric agents once, run on CrewAI, LangGraph, or Strands.

Usage:
    from agentic_fabric.core.decomposer import run_fabric_agent_auto, get_runner, detect_framework
    from agentic_fabric.core.discovery import discover_packages, get_fabric_agent_config
    from agentic_fabric.core.manager import ManagerAgent

    # Auto-detect framework and run a fabric agent
    packages = discover_packages()
    config = get_fabric_agent_config(packages["my-package"], "reviewer")
    result = run_fabric_agent_auto(config, inputs={"task": "..."})

    # Or get a specific runner
    runner = get_runner("crewai")  # or "langgraph", "strands"
    fabric_agent = runner.build_fabric_agent(config)
    result = runner.run(fabric_agent, inputs)

    # Or use a hierarchical manager agent
    class MyManager(ManagerAgent):
        def __init__(self):
            super().__init__(fabric_agents={
                "design": "design_review",
                "implementation": "implementation_review"
            })

        async def execute_workflow(self, task):
            design = await self.delegate_async("design", task)
            return await self.delegate_async("implementation", design)
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version


try:
    __version__ = version("agentic-fabric")
except PackageNotFoundError:  # pragma: no cover - only hit when not installed
    __version__ = "1.2.0"

# Core exports - framework-agnostic functionality
from agentic_fabric.agentic_data import AgenticData
from agentic_fabric.capabilities import (
    AgentCapabilityProviderMixin,
    AgentCapabilitySpec,
    agent_capability,
    runtime_capability,
    tool_capability,
)
from agentic_fabric.core.decomposer import (
    compose_fabric_agent,
    detect_framework,
    get_available_frameworks,
    get_framework_info,
    get_runner,
    is_framework_available,
    run_fabric_agent_auto,
)
from agentic_fabric.core.discovery import (
    discover_all_framework_configs,
    discover_packages,
    get_fabric_agent_config,
    list_fabric_agents,
)
from agentic_fabric.core.manager import ManagerAgent


__all__ = [
    "AgentCapabilityProviderMixin",
    "AgentCapabilitySpec",
    "AgenticData",
    "ManagerAgent",
    "__version__",
    "agent_capability",
    "compose_fabric_agent",
    "detect_framework",
    "discover_all_framework_configs",
    "discover_packages",
    "get_available_frameworks",
    "get_fabric_agent_config",
    "get_framework_info",
    "get_runner",
    "is_framework_available",
    "list_fabric_agents",
    "run_fabric_agent_auto",
    "runtime_capability",
    "tool_capability",
]
