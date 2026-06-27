"""Framework-specific runners for agentic-fabric.

Each runner implements the same interface but targets a different AI framework:
- CrewAIRunner: Full-featured, best for complex fabric_agents
- LangGraphRunner: Graph-based flows, good for conditional logic
- StrandsRunner: Lightweight, AWS-native

Single-agent runners provide simpler execution without multi-agent overhead:
- LocalCLIRunner: Universal runner for any CLI-based coding agent (aider, claude-code, ollama, etc.)

Usage:
    # Multi-agent fabric_agents
    from agentic_fabric.runners import get_runner

    runner = get_runner("crewai")  # Or "langgraph", "strands", "auto"
    fabric_agent = runner.build_fabric_agent(config)
    result = runner.run(fabric_agent, inputs)

    # Single-agent CLI runners
    from agentic_fabric.core.decomposer import get_cli_runner

    runner = get_cli_runner("aider")
    result = runner.run("Add error handling to auth.py")
"""

from __future__ import annotations

from agentic_fabric.core.decomposer import get_cli_runner, get_framework_info, get_runner
from agentic_fabric.runners.registry import RuntimeSpec, runtime_names, runtime_specs


__all__ = ["RuntimeSpec", "get_cli_runner", "get_framework_info", "get_runner", "runtime_names", "runtime_specs"]
