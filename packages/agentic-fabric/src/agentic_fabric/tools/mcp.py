"""Current Model Context Protocol tool-server primitives.

The public adapter is intentionally provider-neutral. Provider discovery,
credentials, and calls remain in ``vendor-fabric``; this module only maps
agent-facing callables onto the structured tool contract implemented by the
current MCP Python SDK line.
"""

from __future__ import annotations

import asyncio
import inspect
import json

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any


MCP_INSTALL_MESSAGE = "MCP SDK is not installed. Install with: pip install agentic-fabric[mcp]"


@dataclass(frozen=True)
class MCPToolAdapter:
    """One callable exposed through an MCP tool server."""

    name: str
    description: str
    input_schema: Mapping[str, Any]
    handler: Callable[..., Any]
    output_schema: Mapping[str, Any] | None = None


def _require_mcp() -> tuple[Any, ...]:
    """Import the low-level MCP server surface lazily."""
    try:
        from jsonschema import Draft202012Validator
        from jsonschema.exceptions import ValidationError
        from mcp.server import Server
        from mcp.shared.exceptions import MCPError
        from mcp.types import (
            INVALID_PARAMS,
            CallToolResult,
            ListToolsResult,
            TextContent,
            Tool,
        )
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc
    return (
        Server,
        MCPError,
        INVALID_PARAMS,
        CallToolResult,
        ListToolsResult,
        TextContent,
        Tool,
        Draft202012Validator,
        ValidationError,
    )


def _json_text(value: Any) -> str:
    """Serialize an MCP payload for the backwards-compatible text block."""
    return json.dumps(value, indent=2, default=str)


def _default_normalize(value: Any) -> Any:
    """Lower common model/container results to JSON-compatible values."""
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if isinstance(value, Mapping):
        return {key: _default_normalize(item) for key, item in value.items()}
    if isinstance(value, Iterable) and not isinstance(value, str | bytes | bytearray):
        return [_default_normalize(item) for item in value]
    return value


def _default_error(error: Exception, arguments: Mapping[str, Any]) -> str:
    """Return a generic execution diagnostic."""
    return f"{type(error).__name__}: {error}"


def create_tool_server(
    name: str,
    tools: Iterable[MCPToolAdapter],
    *,
    version: str = "",
    instructions: str | None = None,
    normalize_result: Callable[[Any], Any] = _default_normalize,
    format_error: Callable[[Exception, Mapping[str, Any]], str] = _default_error,
    format_unknown_tool: Callable[[str], str] | None = None,
) -> Any:
    """Create an MCP server for a finite collection of tool adapters.

    The server validates every call against the advertised JSON Schema,
    returns both text and structured content, marks execution failures with
    ``isError``, and reports unknown tools as protocol-level invalid requests.
    """
    (
        server_type,
        mcp_error_type,
        invalid_params,
        call_tool_result_type,
        list_tools_result_type,
        text_content_type,
        tool_type,
        validator_type,
        validation_error_type,
    ) = _require_mcp()

    tool_list = list(tools)
    adapters = {tool.name: tool for tool in tool_list}
    if len(adapters) != len(tool_list):
        msg = "MCP tool names must be unique"
        raise ValueError(msg)
    validators: dict[str, Any] = {}
    output_validators: dict[str, Any] = {}
    for tool_name, adapter in adapters.items():
        schema = dict(adapter.input_schema)
        validator_type.check_schema(schema)
        validators[tool_name] = validator_type(schema)
        if adapter.output_schema is not None:
            output_schema = dict(adapter.output_schema)
            validator_type.check_schema(output_schema)
            output_validators[tool_name] = validator_type(output_schema)

    async def list_tools(_context: Any, _params: Any) -> Any:
        return list_tools_result_type(
            tools=[
                tool_type(
                    name=adapter.name,
                    description=adapter.description,
                    input_schema=dict(adapter.input_schema),
                    output_schema=dict(adapter.output_schema) if adapter.output_schema is not None else None,
                )
                for adapter in adapters.values()
            ]
        )

    async def call_tool(_context: Any, params: Any) -> Any:
        adapter = adapters.get(params.name)
        if adapter is None:
            message = format_unknown_tool(params.name) if format_unknown_tool else f"Unknown tool: {params.name}"
            raise mcp_error_type(code=invalid_params, message=message)

        arguments = dict(params.arguments or {})
        try:
            validators[adapter.name].validate(arguments)
            result = adapter.handler(**arguments)
            if inspect.isawaitable(result):
                result = await result
            payload = normalize_result(result)
            output_validator = output_validators.get(adapter.name)
            if output_validator is not None:
                output_validator.validate(payload)
            return call_tool_result_type(
                content=[text_content_type(type="text", text=_json_text(payload))],
                structured_content=payload,
                is_error=False,
            )
        except validation_error_type as exc:
            message = format_error(exc, arguments)
            payload = {"error": message}
            return call_tool_result_type(
                content=[text_content_type(type="text", text=_json_text(payload))],
                structured_content=payload,
                is_error=True,
            )
        except Exception as exc:
            message = format_error(exc, arguments)
            payload = {"error": message}
            return call_tool_result_type(
                content=[text_content_type(type="text", text=_json_text(payload))],
                structured_content=payload,
                is_error=True,
            )

    return server_type(
        name,
        version=version,
        instructions=instructions,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


def run_tool_server(server: Any) -> None:
    """Run an MCP server over stdio with legacy-client compatibility."""
    try:
        from mcp.server.stdio import stdio_server
    except ImportError as exc:
        raise ImportError(MCP_INSTALL_MESSAGE) from exc

    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    asyncio.run(run())


__all__ = ["MCPToolAdapter", "create_tool_server", "run_tool_server"]
