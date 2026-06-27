"""Runner module - executes fabric agents with inputs."""

from __future__ import annotations

from pathlib import Path

from agentic_fabric.core.discovery import discover_packages, get_fabric_agent_config
from agentic_fabric.core.loader import load_fabric_agent_from_config


def run_fabric_agent(
    package_name: str,
    fabric_agent_name: str,
    inputs: dict | None = None,
    workspace_root: Path | None = None,
) -> str:
    """Run a fabric agent from a package with the given inputs.

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
    # Discover packages
    packages = discover_packages(workspace_root)

    if package_name not in packages:
        available = list(packages.keys())
        raise ValueError(f"Package '{package_name}' not found. Available: {available}")

    config_dir = packages[package_name]

    # Load fabric agent configuration
    fabric_agent_config = get_fabric_agent_config(config_dir, fabric_agent_name)

    # Build the fabric agent
    fabric_agent = load_fabric_agent_from_config(fabric_agent_config)

    # Run it
    result = fabric_agent.kickoff(inputs=inputs or {})

    return result.raw if hasattr(result, "raw") else str(result)


def run_fabric_agent_from_path(
    config_dir: Path,
    fabric_agent_name: str,
    inputs: dict | None = None,
) -> str:
    """Run a fabric agent directly from a fabric config directory path.

    Args:
        config_dir: Path to the .fabric/ or runtime-specific config directory.
        fabric_agent_name: Name of the fabric agent to run.
        inputs: Optional dict of inputs to pass to the fabric agent.

    Returns:
        The fabric agent's output as a string.
    """
    fabric_agent_config = get_fabric_agent_config(config_dir, fabric_agent_name)
    fabric_agent = load_fabric_agent_from_config(fabric_agent_config)
    result = fabric_agent.kickoff(inputs=inputs or {})
    return result.raw if hasattr(result, "raw") else str(result)
