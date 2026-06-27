"""Runner module - executes fabric agents with inputs.

This module provides convenience functions that discover and run fabric
agents. It routes through the framework-agnostic decomposer so that
``required_framework`` from framework-specific config directories
(.crewai/, .langgraph/, .strands/) is honored.
"""

from __future__ import annotations

from pathlib import Path

from agentic_fabric.core.decomposer import run_fabric_agent_auto
from agentic_fabric.core.discovery import discover_packages, get_fabric_agent_config


def run_fabric_agent(
    package_name: str,
    fabric_agent_name: str,
    inputs: dict | None = None,
    workspace_root: Path | None = None,
) -> str:
    """Run a fabric agent from a package with the given inputs.

    Routes through the framework-agnostic decomposer, so the
    ``required_framework`` from the config directory is honored.

    Args:
        package_name: Name of the package.
        fabric_agent_name: Name of the fabric agent to run (e.g., 'game_builder').
        inputs: Optional dict of inputs to pass to the fabric agent.
        workspace_root: Optional workspace root path.

    Returns:
        The fabric agent's output as a string.

    Raises:
        ValueError: If package or fabric agent not found.
    """
    packages = discover_packages(workspace_root)

    if package_name not in packages:
        available = list(packages.keys())
        raise ValueError(f"Package '{package_name}' not found. Available: {available}")

    config_dir = packages[package_name]
    fabric_agent_config = get_fabric_agent_config(config_dir, fabric_agent_name)
    return run_fabric_agent_auto(fabric_agent_config, inputs=inputs or {})


def run_fabric_agent_from_path(
    config_dir: Path,
    fabric_agent_name: str,
    inputs: dict | None = None,
) -> str:
    """Run a fabric agent directly from a fabric config directory path.

    Routes through the framework-agnostic decomposer, so the
    ``required_framework`` from the config directory is honored.

    Args:
        config_dir: Path to the .fabric/ or runtime-specific config directory.
        fabric_agent_name: Name of the fabric agent to run.
        inputs: Optional dict of inputs to pass to the fabric agent.

    Returns:
        The fabric agent's output as a string.
    """
    fabric_agent_config = get_fabric_agent_config(config_dir, fabric_agent_name)
    return run_fabric_agent_auto(fabric_agent_config, inputs=inputs or {})
