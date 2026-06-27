"""MCP adapter for vendor-fabric Meshy capabilities.

Meshy provider calls stay in vendor-fabric. This agentic-fabric module only
decides how those provider capabilities become MCP tools.
"""

from __future__ import annotations

import asyncio
import json

from collections.abc import Callable, Iterable, Mapping
from typing import Any, cast


MCP_INSTALL_MESSAGE = "MCP SDK not installed. Install with: pip install agentic-fabric[mcp]"
VENDOR_INSTALL_MESSAGE = (
    "vendor-fabric[meshy] is required for Meshy MCP adapters. Install it in the same environment."
)


def _require_meshy_tool_definitions() -> list[dict[str, Any]]:
    """Load Meshy capability metadata from vendor-fabric lazily."""
    try:
        from vendor_fabric.meshy.tools import TOOL_DEFINITIONS
    except ImportError as exc:
        raise ImportError(VENDOR_INSTALL_MESSAGE) from exc
    return list(TOOL_DEFINITIONS)


def _schema_for_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    """Return an MCP input schema for one Meshy capability definition."""
    schema = definition.get("schema")
    if schema is None:
        return {"type": "object", "properties": {}, "required": []}

    model_json_schema = getattr(schema, "model_json_schema", None)
    if callable(model_json_schema):
        generated = model_json_schema()
        return {
            "type": "object",
            "properties": generated.get("properties", {}),
            "required": generated.get("required", []),
        }

    return {"type": "object", "properties": {}, "required": []}


def _create_mcp_tools() -> list[tuple[Any, Callable[..., Any]]]:
    """Create MCP tool definitions from Meshy provider capabilities."""
    try:
        from mcp.types import Tool
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    mcp_tools: list[tuple[Any, Callable[..., Any]]] = []
    for definition in _require_meshy_tool_definitions():
        func = definition["func"]
        tool = Tool(
            name=str(definition["name"]),
            description=str(definition.get("description") or definition["name"]),
            inputSchema=_schema_for_definition(definition),
        )
        mcp_tools.append((tool, func))

    return mcp_tools


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
    """Lower Meshy tool results to JSON-compatible redacted data."""
    if hasattr(result, "model_dump"):
        result = result.model_dump()
    elif isinstance(result, Iterable) and not isinstance(result, str | bytes | bytearray | Mapping):
        result = [item.model_dump() if hasattr(item, "model_dump") else item for item in result]
    result = _to_builtin(result)
    if isinstance(result, set | frozenset):
        result = [_to_builtin(item) for item in result]
    return _redact_sensitive_data(result)


def _tool_error_payload(error: object, *, values: Iterable[Any] | None = None) -> dict[str, str]:
    """Return an MCP-safe error payload without raw secret values."""
    return {"error": _redact_sensitive_text(error, values=values)}


def _tool_payload_text(payload: Any) -> str:
    """Return a serialized MCP text payload."""
    try:
        from extended_data.io import wrap_raw_data_for_export
    except ImportError:
        return json.dumps(payload, indent=2, default=str)
    return wrap_raw_data_for_export(payload, allow_encoding="json", indent_2=True)


def _tool_result_text(result: Any) -> str:
    """Return a serialized Meshy MCP result."""
    return _tool_payload_text(_jsonable_tool_result(result))


def create_server() -> Any:
    """Create an MCP server with Meshy provider capabilities."""
    try:
        from mcp.server import Server
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    server = Server("meshy-ai")
    mcp_tools = _create_mcp_tools()
    tool_handlers = {tool.name: func for tool, func in mcp_tools}
    tool_list = [tool for tool, _ in mcp_tools]

    tool_decorator = cast(Callable[[], Callable[[Callable[..., Any]], Callable[..., Any]]], server.list_tools)
    call_decorator = cast(Callable[[], Callable[[Callable[..., Any]], Callable[..., Any]]], server.call_tool)

    @tool_decorator()
    async def list_tools() -> list[Any]:
        return tool_list

    @call_decorator()
    async def call_tool(name: str, arguments: dict[str, Any] | None) -> list[Any]:
        from mcp.types import TextContent

        tool_arguments = arguments or {}
        handler = tool_handlers.get(name)
        if not handler:
            return [
                TextContent(
                    type="text",
                    text=_tool_payload_text(_tool_error_payload(f"Unknown tool: {name}")),
                )
            ]

        try:
            result = handler(**tool_arguments)
            return [TextContent(type="text", text=_tool_result_text(result))]
        except Exception as exc:
            return [
                TextContent(
                    type="text",
                    text=_tool_payload_text(_tool_error_payload(exc, values=tool_arguments.values())),
                )
            ]

    return server


def run_server(server: Any | None = None) -> None:
    """Run the Meshy MCP adapter over stdio."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    if server is None:
        server = create_server()

    async def main() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(main())


def main() -> None:
    """Entry point for the Meshy MCP adapter."""
    run_server()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["create_server", "main", "run_server"]
