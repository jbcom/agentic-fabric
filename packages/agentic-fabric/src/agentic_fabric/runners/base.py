"""Base runner interface for framework-specific implementations.

All runners must implement this interface to ensure consistent behavior
across CrewAI, LangGraph, and Strands.

# Runner Implementation Guide

To create a new runner for a framework:

1. **Subclass BaseRunner**:
   ```python
   from agentic_fabric.runners.base import BaseRunner

   class MyFrameworkRunner(BaseRunner):
       framework_name = "myframework"
   ```

2. **Implement required methods**:
   - `build_fabric_agent()` - Convert universal config to a runtime-native fabric agent
   - `run()` - Execute the fabric agent and return string output
   - `build_agent()` - Create framework-specific agent
   - `build_task()` - Create framework-specific task

3. **Register in decomposer** (core/decomposer.py):
   - Add to `FRAMEWORK_PRIORITY`
   - Add case to `get_runner()`

4. **Add optional dependency** (pyproject.toml):
   ```toml
   [project.optional-dependencies]
   myframework = ["myframework-package>=1.0"]
   ```

# Example Runner

```python
class SimpleRunner(BaseRunner):
    framework_name = "simple"

    def __init__(self):
        try:
            import simple_framework
        except ImportError as e:
            raise RuntimeError("simple_framework not installed") from e

    def build_fabric_agent(self, fabric_agent_config):
        # Use dict to allow lookup by agent name
        agents = {
            name: self.build_agent(cfg)
            for name, cfg in fabric_agent_config.get("agents", {}).items()
        }

        tasks = []
        for task_name, task_cfg in fabric_agent_config.get("tasks", {}).items():
            agent_name = task_cfg.get("agent")
            agent = agents[agent_name]
            tasks.append(self.build_task(task_cfg, agent))

        return {"agents": list(agents.values()), "tasks": tasks}

    def run(self, fabric_agent, inputs):
        # Execute and return string
        return "Result from simple framework"

    def build_agent(self, agent_config, tools=None):
        return {"role": agent_config["role"], "tools": tools or []}

    def build_task(self, task_config, agent):
        return {"description": task_config["description"], "agent": agent}
```
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from agentic_fabric.capabilities import AgentCapabilityProviderMixin, runtime_capability


class BaseRunner(AgentCapabilityProviderMixin, ABC):
    """Abstract base class for framework runners.

    Each framework runner converts agentic-fabric's universal fabric agent format
    into framework-specific objects and executes them.

    Attributes:
        framework_name: String identifier for this framework (e.g., "crewai",
            "langgraph", "strands"). Used for logging and framework selection.

    Example:
        Basic runner usage with auto-detection:

        ```python
        from agentic_fabric.core.decomposer import get_runner

        # Auto-detect best available framework
        runner = get_runner()

        fabric_agent_config = {
            "name": "research_fabric_agent",
            "agents": {
                "researcher": {
                    "role": "Senior Researcher",
                    "goal": "Find comprehensive information",
                    "backstory": "Expert researcher with years of experience"
                }
            },
            "tasks": {
                "research_task": {
                    "description": "Research the topic thoroughly",
                    "expected_output": "Detailed research report",
                    "agent": "researcher"
                }
            }
        }

        # Build and run in one step
        result = runner.build_and_run(fabric_agent_config, {"topic": "AI safety"})
        print(result)
        ```
    """

    framework_name: str = "base"

    @runtime_capability(
        "build_fabric_agent",
        description="Convert universal fabric agent configuration into a runtime-native fabric agent object.",
    )
    @abstractmethod
    def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
        """Build a framework-specific fabric agent from configuration.

        This is the main method that converts agentic-fabric's universal
        YAML-based fabric agent configuration into the framework's native objects.

        Args:
            fabric_agent_config: Universal fabric agent configuration dict containing:
                - name (str): Fabric agent name for identification
                - description (str): What the fabric agent does
                - agents (dict): Dict mapping agent names to agent configs.
                  Each agent config has:
                    - role (str): Agent's role/title
                    - goal (str): What the agent aims to achieve
                    - backstory (str): Agent's background/expertise
                    - tools (list[str], optional): Tool names to enable
                    - llm (str, optional): Model override
                    - allow_delegation (bool, optional): Can delegate to others
                - tasks (dict): Dict mapping task names to task configs.
                  Each task config has:
                    - description (str): What to do
                    - expected_output (str): What output looks like
                    - agent (str): Name of agent to execute this task
                    - context (list[str], optional): Names of prior tasks
                - knowledge_paths (list[Path], optional): Directories with
                  knowledge files (.md, .txt, etc.)
                - process (str, optional): "sequential" or "hierarchical"
                - required_framework (str, optional): Enforced framework

        Returns:
            Framework-specific fabric agent object. Type varies by framework:
                - CrewAI: crewai.Crew
                - LangGraph: Compiled StateGraph
                - Strands: strands.Agent

        Raises:
            ValueError: If configuration is invalid (e.g., unknown agent
                referenced in task).
            RuntimeError: If framework is not available.

        Example:
            ```python
            runner = CrewAIRunner()
            fabric_agent = runner.build_fabric_agent({
                "name": "writer_fabric_agent",
                "agents": {
                    "writer": {
                        "role": "Technical Writer",
                        "goal": "Create clear documentation",
                        "backstory": "10 years writing experience"
                    }
                },
                "tasks": {
                    "write_docs": {
                        "description": "Write API documentation for {topic}",
                        "expected_output": "Markdown documentation file",
                        "agent": "writer"
                    }
                }
            })
            ```
        """

    @runtime_capability("run", description="Execute a runtime-native fabric agent object.")
    @abstractmethod
    def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
        r"""Execute the fabric agent with inputs.

        Runs the previously built fabric agent with the given inputs. This method
        handles the framework-specific execution and normalizes the output
        to a string.

        Args:
            fabric_agent: Framework-specific fabric agent object from build_fabric_agent().
                Type depends on framework:
                - CrewAI: crewai.Crew instance
                - LangGraph: Compiled StateGraph
                - Strands: strands.Agent instance
            inputs: Input dict to pass to the fabric agent. Keys are typically
                variable names used in task descriptions (e.g., {topic}
                in description becomes inputs["topic"]).

        Returns:
            Fabric agent output as a string. For complex outputs, the raw text
            is returned; parsing is left to the caller.

        Raises:
            RuntimeError: If fabric agent execution fails.

        Example:
            ```python
            # CrewAI runner example
            result = runner.run(fabric_agent, {"topic": "machine learning"})
            print(result)  # "## Machine Learning Report\\n\\n..."

            # LangGraph runner example
            result = runner.run(graph, {"input": "analyze this code"})
            ```
        """

    @runtime_capability("build_and_run", aliases=("run_fabric_agent",), description="Build and execute a fabric agent in one call.")
    def build_and_run(
        self,
        fabric_agent_config: dict[str, Any],
        inputs: dict[str, Any] | None = None,
    ) -> str:
        """Convenience method to build and run in one step.

        Args:
            fabric_agent_config: Fabric agent configuration.
            inputs: Optional inputs for the fabric agent.

        Returns:
            Fabric agent output as string.
        """
        fabric_agent = self.build_fabric_agent(fabric_agent_config)
        return self.run(fabric_agent, inputs or {})

    @runtime_capability("build_agent", description="Create one runtime-native agent object.")
    @abstractmethod
    def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
        """Build a framework-specific agent.

        Creates a single agent from the universal configuration. Called by
        build_fabric_agent() for each agent in the fabric agent.

        Args:
            agent_config: Agent configuration dict containing:
                - role (str): Agent's role/title (e.g., "Senior Researcher")
                - goal (str): What the agent aims to achieve
                - backstory (str): Agent's background and expertise
                - llm (str, optional): Model name to override default
                - allow_delegation (bool, optional): Can delegate tasks
                - verbose (bool, optional): Enable verbose output
            tools: Optional list of tool instances to give the agent.
                Tools should already be resolved/instantiated.

        Returns:
            Framework-specific agent object:
                - CrewAI: crewai.Agent
                - LangGraph: Compiled ReAct agent graph
                - Strands: strands.Agent

        Example:
            ```python
            # CrewAI
            agent = runner.build_agent({
                "role": "Data Analyst",
                "goal": "Analyze data and provide insights",
                "backstory": "Expert in statistical analysis"
            }, tools=[search_tool, calculator_tool])
            ```
        """

    @runtime_capability("build_task", description="Create one runtime-native task object.")
    @abstractmethod
    def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
        """Build a framework-specific task.

        Creates a single task from the universal configuration. Called by
        build_fabric_agent() for each task in the fabric agent.

        Note: Some frameworks (like CrewAI) support additional parameters
        beyond the base signature. Subclasses may extend this method with
        optional parameters like `context` for task dependencies.

        Args:
            task_config: Task configuration dict containing:
                - description (str): What the task should accomplish.
                  Can include {placeholders} for runtime inputs.
                - expected_output (str): Description of expected output format
                - async_execution (bool, optional): Run asynchronously
                - human_input (bool, optional): Request human feedback
            agent: Framework-specific agent to assign to this task.
                Must be the return value from build_agent().

        Returns:
            Framework-specific task object:
                - CrewAI: crewai.Task
                - LangGraph: dict (tasks are stored as config)
                - Strands: dict (tasks are stored as config)

        Example:
            ```python
            # Basic task
            task = runner.build_task({
                "description": "Research {topic} thoroughly",
                "expected_output": "Comprehensive research report"
            }, agent=researcher_agent)

            # CrewAI with context (extended signature)
            task = crewai_runner.build_task(
                task_config,
                agent,
                context=[prior_research_task]  # CrewAI-specific
            )
            ```
        """

    @runtime_capability("get_llm", description="Return the runtime-compatible LLM object.")
    def get_llm(self, model: str | None = None) -> Any:
        """Get the LLM for this framework.

        Retrieves or creates an LLM instance. The default implementation
        uses agentic-fabric's shared LLM configuration. Subclasses may
        override for framework-specific LLM handling.

        Args:
            model: Optional model name override. If None, uses DEFAULT_MODEL
                from agentic_fabric.config.llm (usually claude-sonnet-4-20250514).

        Returns:
            Framework-specific LLM object, or None if the LLM module
            is not available (framework may have its own default).
                - CrewAI: LiteLLM-compatible LLM
                - LangGraph: langchain ChatModel
                - Strands: Uses model_id directly

        Example:
            ```python
            # Use default model
            llm = runner.get_llm()

            # Use specific model
            llm = runner.get_llm("claude-haiku-4-5-20251001")

            # In LangGraphRunner (overridden)
            llm = runner.get_llm("claude-sonnet-4-20250514")  # Returns ChatAnthropic
            ```
        """
        # Default implementation - subclasses can override
        # Import lazily to avoid requiring crewai at module load time.
        # config.llm is a core module with no optional deps — if it can't import,
        # that's a broken install, so let the ImportError propagate rather than
        # silently returning None and using a wrong default model.
        from agentic_fabric.config.llm import DEFAULT_MODEL, get_llm

        # Use default model if none specified to avoid AttributeError
        return get_llm(model or DEFAULT_MODEL)
