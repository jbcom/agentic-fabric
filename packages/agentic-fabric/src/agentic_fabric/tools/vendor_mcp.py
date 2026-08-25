"""MCP adapter for public ``vendor-fabric`` capabilities.

Provider discovery, capability routing, credentials, and connector calls stay
in ``vendor-fabric``. This module converts that public facade into MCP tools
without importing connector implementations or private registry functions.
"""

from __future__ import annotations

import inspect
import logging
import re
import types

from collections.abc import Callable, Mapping
from typing import Any, get_args, get_origin, get_type_hints

from agentic_fabric.tools.mcp import MCP_INSTALL_MESSAGE as _MCP_INSTALL_MESSAGE
from agentic_fabric.tools.mcp import MCPToolAdapter, create_tool_server, run_tool_server


logger = logging.getLogger(__name__)

MCP_INSTALL_MESSAGE = _MCP_INSTALL_MESSAGE
VENDOR_INSTALL_MESSAGE = "vendor-fabric is required by agentic-fabric. Reinstall agentic-fabric in this environment."


def _install_error(message: str, error: ImportError) -> ImportError:
    """Build install guidance without hiding the actual failed import."""
    detail = str(error)
    if detail:
        return ImportError(f"{message}\nOriginal import error: {detail}")
    return ImportError(message)


def _require_vendor_fabric() -> Any:
    """Load only the public vendor-fabric package surface."""
    try:
        import vendor_fabric
    except ImportError as exc:
        raise _install_error(VENDOR_INSTALL_MESSAGE, exc) from exc
    return vendor_fabric


def _annotation_schema(annotation: Any) -> dict[str, Any]:
    """Map a Python annotation to the useful subset of JSON Schema."""
    if annotation in {inspect.Parameter.empty, Any}:
        return {}
    if annotation is str:
        return {"type": "string"}
    if annotation is int:
        return {"type": "integer"}
    if annotation is float:
        return {"type": "number"}
    if annotation is bool:
        return {"type": "boolean"}
    if annotation is type(None):
        return {"type": "null"}

    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is list:
        schema: dict[str, Any] = {"type": "array"}
        if arguments:
            schema["items"] = _annotation_schema(arguments[0])
        return schema
    if origin is dict:
        return {"type": "object"}
    if origin in {types.UnionType, __import__("typing").Union}:
        return {"anyOf": [_annotation_schema(argument) for argument in arguments]}
    return {}


def _get_method_schema(method: Callable[..., Any]) -> dict[str, Any]:
    """Generate an MCP input schema from a provider method signature."""
    signature = inspect.signature(method)
    try:
        type_hints = get_type_hints(method)
    except (NameError, TypeError):
        logger.warning(
            "Could not resolve type hints for %r; using unconstrained schemas for unresolved parameters.",
            method,
            exc_info=True,
        )
        type_hints = {}

    properties: dict[str, dict[str, Any]] = {}
    required: list[str] = []
    additional_properties = False
    doc_lines = method.__doc__.splitlines() if method.__doc__ else []

    for name, parameter in signature.parameters.items():
        if name in {"self", "cls"} or parameter.kind is inspect.Parameter.VAR_POSITIONAL:
            continue
        if parameter.kind is inspect.Parameter.VAR_KEYWORD:
            additional_properties = True
            continue

        annotation = type_hints.get(name, parameter.annotation)
        prop = _annotation_schema(annotation)
        for line in doc_lines:
            if f"{name.lower()}:" in line.lower():
                prop["description"] = line.split(":", 1)[-1].strip()
                break

        if parameter.default is inspect.Parameter.empty:
            required.append(name)
        else:
            prop["default"] = parameter.default
        properties[name] = prop

    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": additional_properties,
    }


def _make_schema(required: set[str], optional: dict[str, Any]) -> dict[str, Any]:
    """Build an object schema for a catalog tool with shared defaults."""
    properties: dict[str, Any] = {"include_unavailable": {"type": "boolean", "default": True}}
    for name, spec in optional.items():
        properties[name] = dict(spec)
    return {
        "type": "object",
        "properties": properties,
        "required": list(required),
        "additionalProperties": False,
    }


def _catalog_tool_adapters(vendor_fabric: Any) -> list[MCPToolAdapter]:
    """Build credential-free adapters from public vendor catalog functions."""
    definitions = (
        (
            "fabric_vendors_list",
            "List vendors registered in the fabric catalog.",
            _make_schema(set(), {}),
            vendor_fabric.list_connectors,
        ),
        (
            "fabric_vendors_list_available",
            "List vendors currently available in this environment.",
            _make_schema(set(), {}),
            vendor_fabric.list_available_connectors,
        ),
        (
            "fabric_vendors_list_info",
            "List vendor catalog metadata.",
            _make_schema(set(), {}),
            vendor_fabric.list_connector_info,
        ),
        (
            "fabric_vendor_get_info",
            "Get catalog metadata for one vendor.",
            _make_schema({"name"}, {"name": {"type": "string"}}),
            vendor_fabric.get_connector_info,
        ),
        (
            "fabric_vendors_list_categories",
            "List vendor categories in the fabric catalog.",
            _make_schema(set(), {}),
            vendor_fabric.list_connector_categories,
        ),
        (
            "fabric_vendors_list_capabilities",
            "List vendor capabilities in the fabric catalog.",
            _make_schema(set(), {}),
            vendor_fabric.list_connector_capabilities,
        ),
        (
            "fabric_vendors_list_by_category",
            "List vendor catalog entries for a category.",
            _make_schema({"category"}, {"category": {"type": "string"}}),
            vendor_fabric.list_connectors_by_category,
        ),
        (
            "fabric_vendors_list_by_capability",
            "List vendor catalog entries for a capability.",
            _make_schema({"capability"}, {"capability": {"type": "string"}}),
            vendor_fabric.list_connectors_by_capability,
        ),
    )
    return [MCPToolAdapter(name, description, schema, handler) for name, description, schema, handler in definitions]


def _metadata_value(metadata: Any, key: str, default: Any = None) -> Any:
    """Read capability metadata from a mapping-like vendor value."""
    if isinstance(metadata, Mapping):
        return metadata.get(key, default)
    getter = getattr(metadata, "get", None)
    if callable(getter):
        return getter(key, default)
    return getattr(metadata, key, default)


def _tool_name(provider: str, operation: str) -> str:
    """Return an MCP-safe, stable name for a vendor capability."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", f"{provider}_{operation}")


def _capability_tool_adapters(vendor_fabric: Any, data: Any) -> list[MCPToolAdapter]:
    """Adapt available ``VendorData`` capability routes to MCP tools."""
    from agentic_fabric.tools.vendor import VendorCapabilityTool

    adapters: list[MCPToolAdapter] = []
    seen: set[str] = set()
    for metadata in data.capabilities(include_unavailable=False):
        provider = str(_metadata_value(metadata, "provider", "")).strip()
        operation = str(_metadata_value(metadata, "operation", "")).strip()
        method_name = str(_metadata_value(metadata, "method", operation)).strip()
        if not provider or not operation or not method_name:
            continue

        connector_class = vendor_fabric.get_connector_class(provider)
        method = getattr(connector_class, method_name)
        name = _tool_name(provider, operation)
        if name in seen:
            msg = f"Vendor capabilities collide on MCP tool name {name!r}"
            raise ValueError(msg)
        seen.add(name)
        description = str(_metadata_value(metadata, "description", "")).strip()
        if not description and method.__doc__:
            description = method.__doc__.splitlines()[0].strip()
        handler = VendorCapabilityTool.from_metadata(metadata, data=data)
        adapters.append(
            MCPToolAdapter(
                name=name,
                description=description or f"Run {provider}.{operation} through vendor-fabric.",
                input_schema=_get_method_schema(method),
                handler=handler,
            )
        )
    return adapters


def _to_builtin(value: Any) -> Any:
    """Lower Extended Data and model values to built-in containers."""
    from extended_data.containers import to_builtin

    return to_builtin(value.model_dump() if hasattr(value, "model_dump") else value)


def _jsonable_tool_result(result: Any) -> Any:
    """Lower provider results to JSON-compatible redacted data."""
    from extended_data.primitives.redaction import redact_sensitive_data

    result = _to_builtin(result)
    if isinstance(result, set | frozenset):
        result = [_to_builtin(item) for item in result]
    return redact_sensitive_data(result)


def _tool_error_text(error: Exception, arguments: Mapping[str, Any]) -> str:
    """Return an MCP-safe execution diagnostic without raw argument values."""
    from extended_data.primitives.redaction import redact_sensitive_text

    redacted = redact_sensitive_text(error, values=arguments.values())
    return f"{type(error).__name__}: {redacted}"


def _unknown_tool_text(name: str) -> str:
    """Return an MCP-safe unknown-tool protocol diagnostic."""
    from extended_data.primitives.redaction import redact_sensitive_text

    return f"Unknown tool: {redact_sensitive_text(name)}"


def create_server(data: Any | None = None) -> Any:
    """Create an MCP server exposing the public vendor capability facade."""
    from agentic_fabric import AgenticData, __version__

    vendor_fabric = _require_vendor_fabric()
    data = data or AgenticData()
    tools = [*_catalog_tool_adapters(vendor_fabric), *_capability_tool_adapters(vendor_fabric, data)]
    return create_tool_server(
        "vendor-fabric",
        tools,
        version=__version__,
        instructions=(
            "Use catalog tools to inspect provider availability, then call only exposed provider capability tools. "
            "Provider credentials and execution are handled by vendor-fabric."
        ),
        normalize_result=_jsonable_tool_result,
        format_error=_tool_error_text,
        format_unknown_tool=_unknown_tool_text,
    )


def run_server(server: Any | None = None) -> None:
    """Run the vendor MCP adapter over stdio."""
    run_tool_server(server or create_server())


def main() -> None:
    """Run the vendor MCP console entry point."""
    run_server()


if __name__ == "__main__":  # pragma: no cover
    main()


__all__ = ["create_server", "main", "run_server"]
