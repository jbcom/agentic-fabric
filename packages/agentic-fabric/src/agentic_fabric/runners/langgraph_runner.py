"""LangGraph runner implementation.

LangGraph excels at:
- Complex conditional flows
- State management
- Cycles and loops
- Integration with LangChain ecosystem
"""

from __future__ import annotations

from typing import Any

from agentic_fabric.runners.base import BaseRunner
from agentic_fabric.runners.registry import install_command
from agentic_fabric.tools.adapters import resolve_langgraph_tools


class LangGraphRunner(BaseRunner):
    """Runner that uses LangGraph for fabric agent execution."""

    framework_name = "langgraph"

    def __init__(self):
        """Initialize LangGraph runner."""
        try:
            import langgraph  # noqa: F401
        except ImportError as e:
            raise RuntimeError(f"LangGraph not installed. Install with: {install_command(self.framework_name)}") from e

    def build_fabric_agent(self, fabric_agent_config: dict[str, Any]) -> Any:
        """Build a LangGraph ReAct agent from fabric agent configuration.

        The current adapter condenses the universal fabric agent configuration into a
        LangGraph prebuilt ReAct agent with the declared tools attached.

        Args:
            fabric_agent_config: Universal fabric agent configuration.

        Returns:
            LangGraph runnable agent.
        """
        from langgraph.prebuilt import create_react_agent

        # For simple fabric agents, create a ReAct agent.
        # More complex fabric agents could be converted to full StateGraphs.

        # Get LLM from config (respects the framework's configuration)
        llm_config = fabric_agent_config.get("llm", {})
        model = llm_config.get("model") if isinstance(llm_config, dict) else llm_config
        llm = self.get_llm(model)

        # Build tools declared by agents in the universal config
        tools = self._build_tools_from_config(fabric_agent_config)

        return create_react_agent(llm, tools)

    def run(self, fabric_agent: Any, inputs: dict[str, Any]) -> str:
        """Execute the LangGraph workflow.

        Args:
            fabric_agent: Compiled LangGraph.
            inputs: Inputs for the workflow.

        Returns:
            Workflow output as string.
        """
        # Convert inputs to messages format
        user_message = inputs.get("input", inputs.get("task", str(inputs)))

        result = fabric_agent.invoke({"messages": [("user", user_message)]})

        # Extract final message
        messages = result.get("messages", [])
        if messages:
            final = messages[-1]
            return final.content if hasattr(final, "content") else str(final)

        return str(result)

    def get_llm(self, model: str | None = None) -> Any:
        """Get LangChain-compatible LLM.

        Args:
            model: Optional model name override.

        Returns:
            LangChain ChatAnthropic LLM.
        """
        from langchain_anthropic import ChatAnthropic

        # Default to Claude Haiku 4.5 if no model specified.
        default_model = "claude-haiku-4-5-20251001"
        return ChatAnthropic(model=model or default_model)

    def build_agent(self, agent_config: dict[str, Any], tools: list | None = None) -> Any:
        """Build a LangGraph-compatible agent.

        Args:
            agent_config: Agent configuration.
            tools: Optional tools.

        Returns:
            LangGraph agent.
        """
        from langgraph.prebuilt import create_react_agent

        # Get LLM from agent config if specified
        llm = self.get_llm(agent_config.get("llm"))
        return create_react_agent(llm, tools or [])

    def build_task(self, task_config: dict[str, Any], agent: Any) -> Any:
        """Build a task representation for LangGraph.

        In LangGraph, tasks are typically represented as graph nodes or
        prompts to agents. Returns a dict for now.

        Args:
            task_config: Task configuration.
            agent: Agent for the task.

        Returns:
            Task configuration dict with agent reference.
        """
        return {
            "description": task_config.get("description", ""),
            "expected_output": task_config.get("expected_output", ""),
            "agent": agent,
        }

    def _build_tools_from_config(self, fabric_agent_config: dict[str, Any]) -> list:
        """Resolve configured agent tools into LangGraph-compatible tools."""
        tool_names: list[str] = []
        for agent_cfg in fabric_agent_config.get("agents", {}).values():
            tool_names.extend(agent_cfg.get("tools", []))
        return resolve_langgraph_tools(tool_names)
