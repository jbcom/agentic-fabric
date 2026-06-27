"""agentic-fabric: Framework-agnostic AI crew orchestration.

Declare crews once, run on CrewAI, LangGraph, or Strands.

Usage:
    from agentic_fabric.core.decomposer import run_crew_auto, get_runner, detect_framework
    from agentic_fabric.core.discovery import discover_packages, get_crew_config
    from agentic_fabric.core.manager import ManagerAgent

    # Auto-detect framework and run a crew
    packages = discover_packages()
    config = get_crew_config(packages["my-package"], "my_crew")
    result = run_crew_auto(config, inputs={"task": "..."})

    # Or get a specific runner
    runner = get_runner("crewai")  # or "langgraph", "strands"
    crew = runner.build_crew(config)
    result = runner.run(crew, inputs)

    # Or use a hierarchical manager agent
    class MyManager(ManagerAgent):
        def __init__(self):
            super().__init__(crews={
                "design": "design_crew",
                "implementation": "impl_crew"
            })

        async def execute_workflow(self, task):
            design = await self.delegate_async("design", task)
            return await self.delegate_async("implementation", design)
"""

from __future__ import annotations


__version__ = "1.0.0"

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
    decompose_crew,
    detect_framework,
    get_available_frameworks,
    get_framework_info,
    get_runner,
    is_framework_available,
    run_crew_auto,
)
from agentic_fabric.core.discovery import (
    discover_all_framework_configs,
    discover_packages,
    get_crew_config,
    list_crews,
)
from agentic_fabric.core.manager import ManagerAgent


__all__ = [
    "AgentCapabilityProviderMixin",
    "AgentCapabilitySpec",
    "AgenticData",
    "ManagerAgent",
    "__version__",
    "agent_capability",
    "decompose_crew",
    "detect_framework",
    "discover_all_framework_configs",
    "discover_packages",
    "get_available_frameworks",
    "get_crew_config",
    "get_framework_info",
    "get_runner",
    "is_framework_available",
    "list_crews",
    "run_crew_auto",
    "runtime_capability",
    "tool_capability",
]
