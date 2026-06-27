"""Core fabric engine for package discovery, loading, and execution."""

from __future__ import annotations

from agentic_fabric.core.discovery import discover_packages, get_fabric_agent_config, load_manifest
from agentic_fabric.core.loader import load_fabric_agent_from_config
from agentic_fabric.core.manager import ManagerAgent
from agentic_fabric.core.runner import run_fabric_agent


__all__ = [
    "ManagerAgent",
    "discover_packages",
    "get_fabric_agent_config",
    "load_fabric_agent_from_config",
    "load_manifest",
    "run_fabric_agent",
]
