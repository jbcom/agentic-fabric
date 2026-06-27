"""Pytest support for agentic-fabric."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pytest_agentic_fabric.mocking import (
    ALL_FRAMEWORK_MODULES,
    CREWAI_MODULES,
    LANGGRAPH_MODULES,
    RUNTIME_MODULES,
    STRANDS_MODULES,
    FabricMocker,
)

__all__ = [
    "ALL_FRAMEWORK_MODULES",
    "CREWAI_MODULES",
    "LANGGRAPH_MODULES",
    "RUNTIME_MODULES",
    "STRANDS_MODULES",
    "FabricMocker",
    "__version__",
]

try:
    __version__ = version("pytest-agentic-fabric")
except PackageNotFoundError:
    __version__ = "0.2.0"
