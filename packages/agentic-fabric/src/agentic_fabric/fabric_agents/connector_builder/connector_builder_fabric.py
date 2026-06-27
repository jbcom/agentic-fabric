"""Connector builder fabric agent.

This script creates and initializes the ``connector_builder`` fabric agent, which is
designed to automatically generate HTTP connector code by scraping API
documentation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agentic_fabric.runners.registry import install_command
from agentic_fabric.tools.registry import resolve_tools
from agentic_fabric.utils import load_config


Agent: Any | None = None
Crew: Any | None = None
Task: Any | None = None


def _load_crewai_classes() -> tuple[Any, Any, Any]:
    """Load CrewAI classes only when the connector-builder fabric agent is used."""
    global Agent, Crew, Task

    if Agent is None or Crew is None or Task is None:
        try:
            from crewai import Agent as ImportedAgent
            from crewai import Crew as ImportedCrew
            from crewai import Task as ImportedTask
        except ImportError as exc:
            msg = f"ConnectorBuilderFabricAgent requires CrewAI. Install with: {install_command('crewai')}"
            raise RuntimeError(msg) from exc

        if Agent is None:
            Agent = ImportedAgent
        if Crew is None:
            Crew = ImportedCrew
        if Task is None:
            Task = ImportedTask

    return Agent, Crew, Task


class ConnectorBuilderFabricAgent:
    """Manage the agents and tasks for the connector builder fabric agent.

    This class loads agent and task configurations from YAML files, instantiates
    the necessary CrewAI components, and provides a method to execute the
    fabric agent's workflow.

    Attributes:
        fabric_agent: An instance of the CrewAI Crew configured with agents and
            tasks for connector building.
    """

    def __init__(self, output_dir: str = "output"):
        """Initializes the ConnectorBuilderFabricAgent.

        Loads agent and task configurations from YAML files, creates Agent
        and Task objects, and assembles them into a Crew.

        Args:
            output_dir: The directory where the generated connector code
                        will be saved.
        """
        agent_cls, crew_cls, task_cls = _load_crewai_classes()
        config_dir = Path(__file__).parent / "config"
        agent_config = load_config(config_dir / "agents.yaml")
        task_config = load_config(config_dir / "tasks.yaml")

        def build_agent(name: str) -> Any:
            config = agent_config[name].copy()
            config["tools"] = resolve_tools(config.get("tools", []))
            return agent_cls(**config)

        # Create Agents
        self.doc_scraper = build_agent("doc_scraper")
        self.api_analyzer = build_agent("api_analyzer")
        self.code_generator = build_agent("code_generator")

        # Create Tasks
        self.scrape_docs = task_cls(**task_config["scrape_docs"])
        self.analyze_api = task_cls(**task_config["analyze_api"])

        generate_code_config = task_config["generate_code"].copy()
        generate_code_config["description"] = generate_code_config["description"].format(output_dir=output_dir)
        self.generate_code = task_cls(**generate_code_config)

        self.fabric_agent = crew_cls(
            agents=[self.doc_scraper, self.api_analyzer, self.code_generator],
            tasks=[self.scrape_docs, self.analyze_api, self.generate_code],
            verbose=True,
        )

    def kickoff(self, inputs: dict) -> str:
        """Start the fabric agent's execution with the given inputs.

        Args:
            inputs: A dictionary containing the necessary inputs for the
                fabric agent's tasks, such as the URL of the API documentation.

        Returns:
            A string representing the result of the fabric agent's execution.
        """
        result = self.fabric_agent.kickoff(inputs=inputs)
        return result.raw if hasattr(result, "raw") else str(result)
