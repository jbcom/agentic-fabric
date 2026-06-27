"""Custom tools for agentic-fabric.

Tool modules are imported lazily so the core package can be imported without
pulling in optional framework dependencies like CrewAI or scraping extras.
"""

from __future__ import annotations

from contextlib import suppress
from importlib import import_module
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:
    from agentic_fabric.tools.file_tools import DirectoryListTool, GameCodeReaderTool, GameCodeWriterTool
    from agentic_fabric.tools.scraping_tools import CrawlWebsiteTool, ScrapeWebsiteTool
    from agentic_fabric.tools.vendor import VendorCapabilityTool, vendor_capability_tools


def _load_attr(module_name: str, attr_name: str) -> Any:
    module = import_module(module_name)
    return getattr(module, attr_name)


def __getattr__(name: str) -> Any:
    if name in {"DirectoryListTool", "GameCodeReaderTool", "GameCodeWriterTool"}:
        return _load_attr("agentic_fabric.tools.file_tools", name)
    if name in {"CrawlWebsiteTool", "ScrapeWebsiteTool"}:
        return _load_attr("agentic_fabric.tools.scraping_tools", name)
    if name in {"VendorCapabilityTool", "vendor_capability_tools"}:
        return _load_attr("agentic_fabric.tools.vendor", name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def get_file_tools() -> list[Any]:
    """Get the standard file manipulation tools."""
    return [
        __getattr__("GameCodeReaderTool")(),
        __getattr__("GameCodeWriterTool")(),
        __getattr__("DirectoryListTool")(),
    ]


def get_scraping_tools() -> list[Any]:
    """Get the web scraping tools."""
    return [
        __getattr__("ScrapeWebsiteTool")(),
        __getattr__("CrawlWebsiteTool")(),
    ]


def get_all_tools() -> list[Any]:
    """Get all available tools."""
    tools = get_file_tools()

    with suppress(ImportError):
        tools.extend(get_scraping_tools())

    with suppress(AttributeError, ImportError, RuntimeError):
        tools.extend(__getattr__("vendor_capability_tools")(include_unavailable=False))

    return tools


__all__ = [
    "CrawlWebsiteTool",
    "DirectoryListTool",
    "GameCodeReaderTool",
    "GameCodeWriterTool",
    "ScrapeWebsiteTool",
    "VendorCapabilityTool",
    "get_all_tools",
    "get_file_tools",
    "get_scraping_tools",
    "vendor_capability_tools",
]
