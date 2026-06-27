"""LangGraph runner implementation.

LangGraph excels at:
- Complex conditional flows
- State management
- Cycles and loops
- Integration with LangChain ecosystem
"""

from __future__ import annotations

import os

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

        For single-agent configs, this produces a single ReAct agent.
        For multi-agent configs, each agent is built as a separate ReAct agent
        and tasks are wired into the system prompt as context. A full StateGraph
        with per-task nodes is a future enhancement.

        Args:
            fabric_agent_config: Universal fabric agent configuration.

        Returns:
            LangGraph runnable agent.
        """
        from langgraph.prebuilt import create_react_agent

        # Get LLM from config (respects the framework's configuration)
        llm_config = fabric_agent_config.get("llm", {})
        model = llm_config.get("model") if isinstance(llm_config, dict) else llm_config
        llm = self.get_llm(model)

        # Build tools declared by agents in the universal config
        tools = self._build_tools_from_config(fabric_agent_config)

        # Build a system prompt from the multi-agent config
        system_prompt = self._build_system_prompt(fabric_agent_config)

        # For single-agent configs, create a simple ReAct agent
        agents_config = fabric_agent_config.get("agents", {})
        if len(agents_config) <= 1:
            return create_react_agent(llm, tools, prompt=system_prompt) if system_prompt else create_react_agent(llm, tools)

        # For multi-agent configs, still create a single ReAct agent but
        # with a system prompt that encodes all agent roles and tasks.
        # This preserves the multi-agent intent in the prompt while using
        # the simplest LangGraph execution model.
        return create_react_agent(llm, tools, prompt=system_prompt)

    def _build_system_prompt(self, fabric_agent_config: dict[str, Any]) -> str:
        """Build a system prompt from the fabric agent config for multi-agent cases."""
        parts = []

        description = fabric_agent_config.get("description")
        if description:
            parts.append(f"# Purpose\n{description}")

        agents = fabric_agent_config.get("agents", {})
        if agents and len(agents) > 1:
            parts.append("\n# Agent Roles")
            for agent_name, agent_cfg in agents.items():
                role = agent_cfg.get("role", agent_name)
                goal = agent_cfg.get("goal", "")
                parts.append(f"\n## {role}")
                if goal:
                    parts.append(f"Goal: {goal}")

        tasks = fabric_agent_config.get("tasks", {})
        if tasks:
            parts.append("\n# Tasks")
            for task_name, task_cfg in tasks.items():
                desc = task_cfg.get("description", "")
                if desc:
                    if len(desc) > 200:
                        parts.append(f"\n- {task_name}: {desc[:200]}...")
                    else:
                        parts.append(f"\n- {task_name}: {desc}")

        return "\n".join(parts)

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

        Supports Ollama via OLLAMA_BASE_URL env var, Anthropic via
        ANTHROPIC_API_KEY, and OpenRouter via OPENROUTER_API_KEY.

        Args:
            model: Optional model name override.

        Returns:
            LangChain ChatModel (ChatOllama, ChatAnthropic, or ChatOpenAI).
        """
        # Ollama mode: use ChatOllama for local inference
        ollama_base_url = os.getenv("OLLAMA_BASE_URL")
        if ollama_base_url or os.getenv("AGENTIC_FABRIC_LLM_PROVIDER", "").lower() == "ollama":
            from langchain_ollama import ChatOllama

            ollama_model = model or os.getenv("OLLAMA_MODEL", "qwen2.5:0.5b")
            return ChatOllama(
                model=ollama_model,
                base_url=ollama_base_url or "http://localhost:11434",
                temperature=0.0,
            )

        # Default: Anthropic
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
