"""Pytest support for agentic-fabric."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from pytest_agentic_fabric.plugin import RUNTIME_MODULES

__all__ = ["RUNTIME_MODULES", "__version__"]

try:
    __version__ = version("pytest-agentic-fabric")
except PackageNotFoundError:
    __version__ = "0.0.0"
