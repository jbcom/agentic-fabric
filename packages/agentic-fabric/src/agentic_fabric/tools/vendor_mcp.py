"""MCP adapters for vendor-fabric provider capabilities.

This module lives in agentic-fabric because MCP is a runtime-visible tool
transport. The provider implementation and capability metadata stay in
vendor-fabric and are imported lazily only when the MCP server is created.
"""

from __future__ import annotations

import asyncio
import builtins
import inspect
import json

from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast, get_origin, get_type_hints


MCP_INSTALL_MESSAGE = "MCP SDK not installed. Install with: pip install agentic-fabric[mcp]"
VENDOR_INSTALL_MESSAGE = (
    "vendor-fabric is required for vendor MCP adapters. Install vendor-fabric in the same environment."
)


def _install_error(message: str, error: ImportError) -> ImportError:
    """Build install guidance without hiding the actual failed import."""
    detail = str(error)
    if detail:
        return ImportError(f"{message}\nOriginal import error: {detail}")
    return ImportError(message)


def _require_vendor_fabric() -> tuple[Any, Callable[..., Any]]:
    """Load vendor-fabric registry and surface helpers lazily."""
    try:
        from vendor_fabric import registry
        from vendor_fabric.surface import connector_data_methods
    except ImportError as exc:
        raise _install_error(VENDOR_INSTALL_MESSAGE, exc) from exc
    return registry, connector_data_methods


def _get_method_schema(method: Callable[..., Any]) -> dict[str, Any]:
    """Generate a JSON schema from a provider method signature."""
    sig = inspect.signature(method)
    try:
        type_hints = get_type_hints(method)
    except Exception:
        type_hints = {}
    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []

    for name, param in sig.parameters.items():
        if name in {"self", "cls"}:
            continue

        prop: dict[str, Any] = {"type": "string"}
        ann = type_hints.get(name, param.annotation)
        if ann != inspect.Parameter.empty:
            if ann is int:
                prop = {"type": "integer"}
            elif ann is float:
                prop = {"type": "number"}
            elif ann is bool:
                prop = {"type": "boolean"}
            elif ann is list or get_origin(ann) is list:
                prop = {"type": "array"}
            elif ann is dict or get_origin(ann) is dict:
                prop = {"type": "object"}

        if method.__doc__:
            for line in method.__doc__.split("\n"):
                if f"{name}:" in line.lower():
                    prop["description"] = line.split(":", 1)[-1].strip()
                    break

        if param.default != inspect.Parameter.empty:
            prop["default"] = param.default
        else:
            required.append(name)

        properties[name] = prop

    return {"type": "object", "properties": properties, "required": required}


def _get_public_methods(
    connector_class: builtins.type[Any],
    connector_data_methods: Callable[[builtins.type[Any]], list[tuple[str, Callable[..., Any]]]],
) -> list[tuple[str, Callable[..., Any]]]:
    """Get public provider data methods for MCP exposure."""
    return connector_data_methods(connector_class)


def _connector_classes(registry: Any) -> Mapping[str, builtins.type[Any]]:
    """Return connector classes for runtime method exposure.

    vendor-fabric currently keeps class discovery internal. The MCP adapter
    isolates that private call so catalog tools still work if the public
    surface changes before a stable method-list API is published.
    """
    list_connector_classes = getattr(registry, "_list_connector_classes", None)
    if not callable(list_connector_classes):
        return {}
    return cast(Mapping[str, builtins.type[Any]], list_connector_classes())


def _catalog_tool_definitions(registry: Any) -> dict[str, dict[str, Any]]:
    """Build credential-free vendor catalog MCP tools."""
    include_unavailable_schema: dict[str, Any] = {
        "type": "object",
        "properties": {"include_unavailable": {"type": "boolean", "default": True}},
        "required": [],
    }
    empty_schema: dict[str, Any] = {"type": "object", "properties": {}, "required": []}
    name_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "include_unavailable": {"type": "boolean", "default": True},
        },
        "required": ["name"],
    }
    category_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "category": {"type": "string"},
            "include_unavailable": {"type": "boolean", "default": True},
        },
        "required": ["category"],
    }
    capability_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "capability": {"type": "string"},
            "include_unavailable": {"type": "boolean", "default": True},
        },
        "required": ["capability"],
    }

    return {
        "fabric_vendors_list": {
            "description": "List vendors registered in the fabric catalog.",
            "parameters": include_unavailable_schema,
            "handler": registry.list_connectors,
        },
        "fabric_vendors_list_available": {
            "description": "List vendors currently available in this environment.",
            "parameters": empty_schema,
            "handler": registry.list_available_connectors,
        },
        "fabric_vendors_list_info": {
            "description": "List vendor catalog metadata.",
            "parameters": include_unavailable_schema,
            "handler": registry.list_connector_info,
        },
        "fabric_vendor_get_info": {
            "description": "Get catalog metadata for one vendor.",
            "parameters": name_schema,
            "handler": registry.get_connector_info,
        },
        "fabric_vendors_list_categories": {
            "description": "List vendor categories in the fabric catalog.",
            "parameters": include_unavailable_schema,
            "handler": registry.list_connector_categories,
        },
        "fabric_vendors_list_capabilities": {
            "description": "List vendor capabilities in the fabric catalog.",
            "parameters": include_unavailable_schema,
            "handler": registry.list_connector_capabilities,
        },
        "fabric_vendors_list_by_category": {
            "description": "List vendor catalog entries for a category.",
            "parameters": category_schema,
            "handler": registry.list_connectors_by_category,
        },
        "fabric_vendors_list_by_capability": {
            "description": "List vendor catalog entries for a capability.",
            "parameters": capability_schema,
            "handler": registry.list_connectors_by_capability,
        },
    }


def _to_builtin(value: Any) -> Any:
    try:
        from extended_data.containers import to_builtin
    except ImportError:
        if hasattr(value, "model_dump"):
            return value.model_dump()
        if isinstance(value, Mapping):
            return {key: _to_builtin(item) for key, item in value.items()}
        if isinstance(value, Iterable) and not isinstance(value, str | bytes | bytearray):
            return [_to_builtin(item) for item in value]
        return value
    return to_builtin(value)


def _redact_sensitive_data(value: Any) -> Any:
    try:
        from extended_data.primitives.redaction import redact_sensitive_data
    except ImportError:
        return value
    return redact_sensitive_data(value)


def _redact_sensitive_text(value: object, *, values: Iterable[Any] | None = None) -> str:
    try:
        from extended_data.primitives.redaction import redact_sensitive_text
    except ImportError:
        return str(value)
    return redact_sensitive_text(value, values=values)


def _jsonable_tool_result(result: Any) -> Any:
    """Lower provider tool results to JSON-compatible redacted data."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif isinstance(result, Iterable) and not isinstance(result, str | bytes | bytearray | Mapping):
        result = [item.model_dump() if hasattr(item, "model_dump") else item for item in result]
    result = _to_builtin(result)
    if isinstance(result, set | frozenset):
        result = [_to_builtin(item) for item in result]
    return _redact_sensitive_data(result)


def _tool_error_text(error: Exception, values: Iterable[Any] | None = None) -> str:
    """Return an MCP-safe error string without raw secret values."""
    return f"Error: {type(error).__name__}: {_redact_sensitive_text(error, values=values)}"


def _unknown_tool_text(name: str) -> str:
    """Return an MCP-safe unknown-tool diagnostic."""
    return f"Unknown tool: {_redact_sensitive_text(name)}"


def _tool_result_text(result: Any) -> str:
    """Return a serialized MCP tool result."""
    payload = _jsonable_tool_result(result)
    try:
        from extended_data.io import wrap_raw_data_for_export
    except ImportError:
        return json.dumps(payload, indent=2, default=str)
    return wrap_raw_data_for_export(payload, allow_encoding="json", indent_2=True, default=str)


def create_server() -> Any:
    """Create an MCP server exposing vendor-fabric provider capabilities."""
    try:
        from mcp.server import Server
        from mcp.types import TextContent, Tool
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    registry, connector_data_methods = _require_vendor_fabric()
    server = Server("vendor-fabric")
    tools: dict[str, dict[str, Any]] = _catalog_tool_definitions(registry)

    for connector_name, connector_class in _connector_classes(registry).items():
        for method_name, method in _get_public_methods(connector_class, connector_data_methods):
            if method_name in {"close", "request", "get_input", "register_tool"}:
                continue

            description = method.__doc__.split("\n")[0].strip() if method.__doc__ else ""
            tools[f"{connector_name}_{method_name}"] = {
                "connector": connector_name,
                "method": method_name,
                "description": description or f"{connector_name}.{method_name}()",
                "parameters": _get_method_schema(method),
            }

    tool_decorator = cast(Callable[[], Callable[[Callable[..., Any]], Callable[..., Any]]], server.list_tools)
    call_decorator = cast(Callable[[], Callable[[Callable[..., Any]], Callable[..., Any]]], server.call_tool)

    @tool_decorator()
    async def list_tools() -> list[Tool]:
        return [
            Tool(name=name, description=tool["description"], inputSchema=tool["parameters"])
            for name, tool in tools.items()
        ]

    @call_decorator()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[TextContent]:
        tool_arguments = arguments or {}
        if name not in tools:
            return [TextContent(type="text", text=_unknown_tool_text(name))]

        tool = tools[name]
        handler = tool.get("handler")
        if callable(handler):
            try:
                result = handler(**tool_arguments)
                if inspect.iscoroutine(result):
                    result = await result
                return [TextContent(type="text", text=_tool_result_text(result))]
            except Exception as exc:
                return [TextContent(type="text", text=_tool_error_text(exc, tool_arguments.values()))]

        try:
            connector = registry.get_connector(tool["connector"])
            method = getattr(connector, tool["method"])
            result = method(**tool_arguments)
            if inspect.iscoroutine(result):
                result = await result
            return [TextContent(type="text", text=_tool_result_text(result))]
        except Exception as exc:
            return [TextContent(type="text", text=_tool_error_text(exc, tool_arguments.values()))]

    return server


def run_server(server: Any | None = None) -> None:
    """Run the vendor MCP adapter over stdio."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    if server is None:
        server = create_server()

    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


def main() -> None:
    """Entry point for the vendor MCP adapter."""
    run_server()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["create_server", "main", "run_server"]
