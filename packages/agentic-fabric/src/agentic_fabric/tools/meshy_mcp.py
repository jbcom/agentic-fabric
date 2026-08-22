"""MCP adapter for vendor-fabric Meshy capability definitions."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from agentic_fabric.tools.mcp import MCPToolAdapter, create_tool_server, run_tool_server


VENDOR_INSTALL_MESSAGE = "vendor-fabric[meshy] is required. Install with: pip install agentic-fabric[meshy,mcp]"


def _install_error(message: str, error: ImportError) -> ImportError:
    """Build install guidance without hiding the actual failed import."""
    detail = str(error)
    if detail:
        return ImportError(f"{message}\nOriginal import error: {detail}")
    return ImportError(message)


def _require_meshy_tool_definitions() -> list[dict[str, Any]]:
    """Load Meshy capability metadata from vendor-fabric lazily."""
    try:
        from vendor_fabric.meshy.tools import TOOL_DEFINITIONS
    except ImportError as exc:
        raise _install_error(VENDOR_INSTALL_MESSAGE, exc) from exc
    return list(TOOL_DEFINITIONS)


def _schema_for_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    """Return an MCP input schema for one Meshy capability definition."""
    schema = definition.get("schema")
    model_json_schema = getattr(schema, "model_json_schema", None)
    if not callable(model_json_schema):
        return {"type": "object", "properties": {}, "additionalProperties": False}

    generated = model_json_schema()
    generated.setdefault("type", "object")
    generated.setdefault("properties", {})
    return generated


def _create_mcp_tools() -> list[MCPToolAdapter]:
    """Create MCP adapters from Meshy provider-owned capability metadata."""
    return [
        MCPToolAdapter(
            name=str(definition["name"]),
            description=str(definition.get("description") or definition["name"]),
            input_schema=_schema_for_definition(definition),
            handler=definition["func"],
        )
        for definition in _require_meshy_tool_definitions()
    ]


def _to_builtin(value: Any) -> Any:
    """Lower Extended Data and model values to built-in containers."""
    from extended_data.containers import to_builtin

    return to_builtin(value.model_dump() if hasattr(value, "model_dump") else value)


def _jsonable_tool_result(result: Any) -> Any:
    """Lower Meshy results to JSON-compatible redacted data."""
    from extended_data.primitives.redaction import redact_sensitive_data

    result = _to_builtin(result)
    if isinstance(result, set | frozenset):
        result = [_to_builtin(item) for item in result]
    if isinstance(result, Iterable) and not isinstance(result, str | bytes | bytearray | Mapping):
        result = [_to_builtin(item) for item in result]
    return redact_sensitive_data(result)


def _tool_error_text(error: Exception, arguments: Mapping[str, Any]) -> str:
    """Return an MCP-safe execution diagnostic without raw argument values."""
    from extended_data.primitives.redaction import redact_sensitive_text

    return f"{type(error).__name__}: {redact_sensitive_text(error, values=arguments.values())}"


def _unknown_tool_text(name: str) -> str:
    """Return an MCP-safe unknown-tool protocol diagnostic."""
    from extended_data.primitives.redaction import redact_sensitive_text

    return f"Unknown tool: {redact_sensitive_text(name)}"


def create_server() -> Any:
    """Create an MCP server with Meshy provider capabilities."""
    from agentic_fabric import __version__

    return create_tool_server(
        "meshy-ai",
        _create_mcp_tools(),
        version=__version__,
        instructions="Generate and transform 3D assets through vendor-fabric's Meshy provider facade.",
        normalize_result=_jsonable_tool_result,
        format_error=_tool_error_text,
        format_unknown_tool=_unknown_tool_text,
    )


def run_server(server: Any | None = None) -> None:
    """Run the Meshy MCP adapter over stdio."""
    run_tool_server(server or create_server())


def main() -> None:
    """Run the Meshy MCP console entry point."""
    run_server()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["create_server", "main", "run_server"]
