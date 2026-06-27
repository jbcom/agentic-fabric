"""Single-agent runner base class.

Single-agent runners execute simple, sequential tasks without multi-agent
collaboration overhead. They're ideal for:
- Quick file edits
- Code generation
- Local development
- Sequential workflows

Unlike multi-agent fabric agents, single-agent runners:
- Take a single task string as input
- Execute in one pass without delegation
- Return results directly
- Have minimal configuration overhead
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentic_fabric.capabilities import AgentCapabilityProviderMixin, runtime_capability


class SingleAgentRunner(AgentCapabilityProviderMixin, ABC):
    """Base class for single-agent runners.

    Single-agent runners provide a simpler execution model than multi-agent
    fabric agents. They execute a single task and return the result, without the
    complexity of agent collaboration, delegation, or hierarchical processes.
    """

    runner_name: str = "single_agent"

    @runtime_capability("run", description="Execute one single-agent task.")
    @abstractmethod
    def run(
        self,
        task: str,
        working_dir: str | None = None,
        **kwargs: Any,
    ) -> str:
        """Execute a single task and return the result.

        Args:
            task: The task to execute (e.g., "Add error handling to auth.py").
            working_dir: Optional working directory for execution.
            **kwargs: Additional runner-specific parameters.

        Returns:
            Task output as a string.

        Raises:
            RuntimeError: If execution fails.
        """

    @runtime_capability("is_available", description="Report whether this local runner can execute.")
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this runner is available (dependencies installed, etc.).

        Returns:
            True if the runner can be used.

        Raises:
            NotImplementedError: Subclasses must override this.
        """

    @runtime_capability("required_env_vars", description="List environment variables required by this runner.")
    def get_required_env_vars(self) -> list[str]:
        """Get list of required environment variables.

        Returns:
            List of environment variable names required by this runner.
        """
        # Default implementation - subclasses can override
        return []
