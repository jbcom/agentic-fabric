"""Core CrewAI engine - discovery, loading, and running of package-defined crews."""

from __future__ import annotations

from agentic_fabric.core.discovery import discover_packages, get_crew_config, load_manifest
from agentic_fabric.core.loader import load_crew_from_config
from agentic_fabric.core.manager import ManagerAgent
from agentic_fabric.core.runner import run_crew


__all__ = [
    "ManagerAgent",
    "discover_packages",
    "get_crew_config",
    "load_crew_from_config",
    "load_manifest",
    "run_crew",
]
