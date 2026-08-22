"""Tests for the MCP server and vendor adapters."""

from __future__ import annotations

import asyncio
import builtins
import inspect
import sys
import types

from contextlib import asynccontextmanager
from typing import Any

import pytest

from jsonschema.exceptions import SchemaError

from agentic_fabric.tools import mcp as mcp_server
from agentic_fabric.tools import meshy_mcp, vendor_mcp


class FakeModel:
    """Small Pydantic-like protocol result used by the fake SDK."""

    def __init__(self, **kwargs: Any) -> None:
        self.__dict__.update(kwargs)


class FakeMCPError(Exception):
    """Record a protocol error code and message."""

    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class FakeServer:
    """MCP low-level server stand-in."""

    def __init__(
        self,
        name: str,
        *,
        version: str = "",
        instructions: str | None = None,
        on_list_tools: Any = None,
        on_call_tool: Any = None,
    ) -> None:
        self.name = name
        self.version = version
        self.instructions = instructions
        self.on_list_tools = on_list_tools
        self.on_call_tool = on_call_tool

    def create_initialization_options(self) -> dict[str, bool]:
        return {"ready": True}


class RunnableServer:
    """Server stand-in for stdio lifecycle tests."""

    def __init__(self, calls: list[tuple[Any, ...]]) -> None:
        self.calls = calls

    def create_initialization_options(self) -> dict[str, bool]:
        return {"ready": True}

    async def run(self, read_stream: Any, write_stream: Any, options: Any) -> None:
        self.calls.append((read_stream, write_stream, options))


def install_fake_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install the constructor-based MCP surface used by adapters."""
    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    shared_module = types.ModuleType("mcp.shared")
    exceptions_module = types.ModuleType("mcp.shared.exceptions")
    types_module = types.ModuleType("mcp.types")
    server_module.Server = FakeServer
    exceptions_module.MCPError = FakeMCPError
    types_module.INVALID_PARAMS = -32602
    for name in ("CallToolResult", "ListToolsResult", "TextContent", "Tool"):
        setattr(types_module, name, FakeModel)
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.shared", shared_module)
    monkeypatch.setitem(sys.modules, "mcp.shared.exceptions", exceptions_module)
    monkeypatch.setitem(sys.modules, "mcp.types", types_module)


def install_fake_stdio(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    """Install a fake stdio transport and return the run-call ledger."""
    calls: list[tuple[Any, ...]] = []

    @asynccontextmanager
    async def stdio_server() -> Any:
        yield "read", "write"

    stdio_module = types.ModuleType("mcp.server.stdio")
    stdio_module.stdio_server = stdio_server
    monkeypatch.setitem(sys.modules, "mcp.server.stdio", stdio_module)
    return calls


def reject_imports(monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    """Reject imports for a module prefix while preserving other imports."""
    real_import = builtins.__import__

    def reject(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == prefix or name.startswith(f"{prefix}."):
            raise ImportError(f"blocked {name}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject)


def test_generic_mcp_server_lists_calls_validates_and_reports_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    async def asynchronous(*, value: int) -> dict[str, int]:
        return {"value": value + 1}

    def failure(*, token: str) -> None:
        raise RuntimeError(f"bad {token}")

    server = mcp_server.create_tool_server(
        "demo",
        [
            mcp_server.MCPToolAdapter(
                "increment",
                "Increment a number.",
                {
                    "type": "object",
                    "properties": {"value": {"type": "integer"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
                asynchronous,
            ),
            mcp_server.MCPToolAdapter(
                "failure",
                "Fail safely.",
                {
                    "type": "object",
                    "properties": {"token": {"type": "string"}},
                    "required": ["token"],
                },
                failure,
                output_schema={"type": "object"},
            ),
        ],
        version="2.3",
        instructions="Use carefully.",
    )

    listed = asyncio.run(server.on_list_tools(None, None))
    success = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="increment", arguments={"value": 2})))
    invalid = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="increment", arguments={"value": "x"})))
    failure_result = asyncio.run(
        server.on_call_tool(None, types.SimpleNamespace(name="failure", arguments={"token": "secret"}))
    )

    assert server.name == "demo"
    assert server.version == "2.3"
    assert server.instructions == "Use carefully."
    assert [tool.name for tool in listed.tools] == ["increment", "failure"]
    assert listed.tools[0].input_schema["required"] == ["value"]
    assert listed.tools[1].output_schema == {"type": "object"}
    assert success.structured_content == {"value": 3}
    assert '"value": 3' in success.content[0].text
    assert success.is_error is False
    assert invalid.is_error is True
    assert "ValidationError" in invalid.structured_content["error"]
    assert failure_result.is_error is True
    assert "bad secret" in failure_result.structured_content["error"]

    with pytest.raises(FakeMCPError) as exc_info:
        asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="missing", arguments=None)))
    assert exc_info.value.code == -32602
    assert exc_info.value.message == "Unknown tool: missing"


def test_generic_mcp_server_custom_normalization_and_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    def make_dumpable() -> Dumpable:
        return Dumpable()

    server = mcp_server.create_tool_server(
        "custom",
        [mcp_server.MCPToolAdapter("dump", "Dump.", {"type": "object"}, make_dumpable)],
        normalize_result=lambda value: {"normalized": value.model_dump()},
        format_error=lambda error, arguments: "safe-error",
        format_unknown_tool=lambda name: f"safe:{name}",
    )
    result = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="dump", arguments=None)))
    assert result.structured_content == {"normalized": {"dumped": True}}

    with pytest.raises(FakeMCPError, match="safe:absent"):
        asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="absent", arguments={})))

    assert mcp_server._default_normalize(Dumpable()) == {"dumped": True}
    assert mcp_server._default_normalize({"items": (Dumpable(),)}) == {"items": [{"dumped": True}]}
    assert mcp_server._default_normalize("text") == "text"
    assert mcp_server._default_error(ValueError("bad"), {}) == "ValueError: bad"
    assert mcp_server._json_text({"value": object()}).startswith("{")


def test_generic_mcp_server_rejects_invalid_schema(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    with pytest.raises(SchemaError):
        mcp_server.create_tool_server(
            "bad",
            [mcp_server.MCPToolAdapter("bad", "Bad.", {"type": "not-a-json-type"}, lambda: None)],
        )

    with pytest.raises(SchemaError):
        mcp_server.create_tool_server(
            "bad-output",
            [
                mcp_server.MCPToolAdapter(
                    "bad",
                    "Bad.",
                    {"type": "object"},
                    lambda: None,
                    output_schema={"type": "not-a-json-type"},
                )
            ],
        )


def test_generic_mcp_server_rejects_duplicate_names_and_invalid_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_fake_mcp(monkeypatch)
    duplicate = mcp_server.MCPToolAdapter("same", "Same.", {"type": "object"}, dict)
    with pytest.raises(ValueError, match="must be unique"):
        mcp_server.create_tool_server("duplicate", [duplicate, duplicate])

    invalid_output = mcp_server.MCPToolAdapter(
        "invalid-output",
        "Invalid output.",
        {"type": "object"},
        dict,
        output_schema={"type": "array"},
    )
    server = mcp_server.create_tool_server("output", [invalid_output])
    result = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="invalid-output", arguments={})))
    assert result.is_error is True
    assert result.structured_content["error"].startswith("ValidationError:")


def test_generic_mcp_reports_missing_sdk(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp")
    with pytest.raises(ImportError, match="MCP SDK"):
        mcp_server.create_tool_server("missing", [])


def test_generic_mcp_run_server(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    calls = install_fake_stdio(monkeypatch)
    mcp_server.run_tool_server(RunnableServer(calls))
    assert calls == [("read", "write", {"ready": True})]


def test_generic_mcp_run_server_reports_missing_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp.server.stdio")
    with pytest.raises(ImportError, match="MCP SDK"):
        mcp_server.run_tool_server(RunnableServer([]))


class DemoConnector:
    """Public fake connector class exposed through vendor-fabric."""

    def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Search demo records.

        query: Search text.
        limit: Maximum results.
        """
        return {"query": query, "limit": limit}

    async def async_lookup(self) -> dict[str, bool]:
        """Look up asynchronously."""
        return {"async": True}

    def fail(self, token: str) -> None:
        """Fail with a secret-bearing message."""
        raise RuntimeError(f"connector failed for {token}")


class FakeVendorData:
    """VendorData-shaped facade for adapter tests."""

    def __init__(self, capabilities: list[dict[str, Any]] | None = None) -> None:
        self._capabilities = capabilities or [
            {"provider": "demo", "operation": "search", "method": "search", "description": "Search."},
            {"provider": "demo", "operation": "async_lookup", "method": "async_lookup"},
            {"provider": "demo", "operation": "fail", "method": "fail"},
        ]
        self.active_provider: str | None = None
        self.opens: list[tuple[str, bool]] = []

    def capabilities(self, *, include_unavailable: bool = True) -> list[dict[str, Any]]:
        assert include_unavailable is False
        return self._capabilities

    def open(self, provider: str, *, strict: bool = True) -> FakeVendorData:
        self.active_provider = provider
        self.opens.append((provider, strict))
        return self

    def call(self, operation: str, provider: str, **kwargs: Any) -> Any:
        return getattr(DemoConnector(), operation)(**kwargs)


def install_fake_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> types.ModuleType:
    """Install a public-only fake vendor-fabric package."""
    vendor = types.ModuleType("vendor_fabric")
    vendor.get_connector_class = lambda name: DemoConnector
    vendor.list_connectors = lambda *, include_unavailable=True: ["demo"]
    vendor.list_available_connectors = lambda: ["demo"]
    vendor.list_connector_info = lambda *, include_unavailable=True: [{"name": "demo"}]
    vendor.get_connector_info = lambda name, *, include_unavailable=True: {"name": name}
    vendor.list_connector_categories = lambda *, include_unavailable=True: ["testing"]
    vendor.list_connector_capabilities = lambda *, include_unavailable=True: ["search"]
    vendor.list_connectors_by_category = lambda category, *, include_unavailable=True: [category]
    vendor.list_connectors_by_capability = lambda capability, *, include_unavailable=True: [capability]
    monkeypatch.setitem(sys.modules, "vendor_fabric", vendor)
    return vendor


def test_vendor_mcp_exposes_public_catalog_and_capabilities(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    install_fake_vendor_fabric(monkeypatch)
    data = FakeVendorData()

    server = vendor_mcp.create_server(data)
    listed = asyncio.run(server.on_list_tools(None, None))
    names = {tool.name for tool in listed.tools}
    catalog = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="fabric_vendors_list", arguments=None)))
    search = asyncio.run(
        server.on_call_tool(
            None,
            types.SimpleNamespace(name="demo_search", arguments={"query": "alpha", "limit": 2}),
        )
    )
    asynchronous = asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="demo_async_lookup", arguments={})))
    failure = asyncio.run(
        server.on_call_tool(None, types.SimpleNamespace(name="demo_fail", arguments={"token": "secret-value"}))
    )

    assert server.name == "vendor-fabric"
    assert "fabric_vendors_list" in names
    assert "demo_search" in names
    assert catalog.structured_content == ["demo"]
    assert search.structured_content == {"query": "alpha", "limit": 2}
    assert asynchronous.structured_content == {"async": True}
    assert failure.is_error is True
    assert "secret-value" not in failure.content[0].text
    assert data.opens == [("demo", False)]


def test_vendor_mcp_catalog_and_protocol_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    vendor = install_fake_vendor_fabric(monkeypatch)
    vendor.list_connector_categories = lambda *, include_unavailable=True: (_ for _ in ()).throw(
        RuntimeError("catalog failed")
    )
    server = vendor_mcp.create_server(FakeVendorData())

    failed = asyncio.run(
        server.on_call_tool(None, types.SimpleNamespace(name="fabric_vendors_list_categories", arguments={}))
    )
    assert failed.is_error is True
    assert "catalog failed" in failed.content[0].text

    with pytest.raises(FakeMCPError, match="Unknown tool: missing"):
        asyncio.run(server.on_call_tool(None, types.SimpleNamespace(name="missing", arguments={})))


def test_vendor_mcp_schema_and_metadata_helpers() -> None:
    def typed(
        self: object,
        count: int,
        ratio: float,
        enabled: bool,
        items: list[str],
        payload: dict[str, Any],
        optional: str | None = None,
        *values: str,
        **extra: Any,
    ) -> None:
        """Typed method.

        count: Count value.
        """

    def unresolved(value: MissingType) -> None:  # noqa: F821
        return None

    schema = vendor_mcp._get_method_schema(typed)
    unresolved_schema = vendor_mcp._get_method_schema(unresolved)
    assert schema["properties"]["count"] == {"type": "integer", "description": "Count value."}
    assert schema["properties"]["ratio"]["type"] == "number"
    assert schema["properties"]["enabled"]["type"] == "boolean"
    assert schema["properties"]["items"]["items"] == {"type": "string"}
    assert schema["properties"]["payload"]["type"] == "object"
    assert schema["properties"]["optional"]["anyOf"] == [{"type": "string"}, {"type": "null"}]
    assert schema["properties"]["optional"]["default"] is None
    assert schema["additionalProperties"] is True
    assert unresolved_schema["properties"]["value"] == {}
    assert vendor_mcp._annotation_schema(inspect.Parameter.empty) == {}
    assert vendor_mcp._metadata_value({"name": "mapping"}, "name") == "mapping"
    assert vendor_mcp._metadata_value(types.SimpleNamespace(get=lambda key, default: "getter"), "name") == "getter"
    assert vendor_mcp._metadata_value(types.SimpleNamespace(name="attribute"), "name") == "attribute"
    assert vendor_mcp._metadata_value(object(), "missing", "fallback") == "fallback"
    assert vendor_mcp._tool_name("demo provider", "list/things") == "demo_provider_list_things"
    assert str(vendor_mcp._install_error("install", ImportError())) == "install"
    assert "Original import error: detail" in str(vendor_mcp._install_error("install", ImportError("detail")))


def test_vendor_mcp_skips_bad_metadata_and_rejects_collisions(monkeypatch: pytest.MonkeyPatch) -> None:
    vendor = install_fake_vendor_fabric(monkeypatch)
    assert vendor_mcp._capability_tool_adapters(vendor, FakeVendorData([{}])) == []

    data = FakeVendorData(
        [
            {"provider": "demo", "operation": "async lookup", "method": "async_lookup"},
            {"provider": "demo", "operation": "async_lookup", "method": "async_lookup"},
        ]
    )
    with pytest.raises(ValueError, match="collide"):
        vendor_mcp._capability_tool_adapters(vendor, data)


def test_vendor_mcp_reports_missing_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "vendor_fabric")
    with pytest.raises(ImportError, match="required by agentic-fabric"):
        vendor_mcp._require_vendor_fabric()


def test_vendor_mcp_normalization_helpers() -> None:
    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    assert vendor_mcp._jsonable_tool_result(Dumpable()) == {"dumped": True}
    assert sorted(vendor_mcp._jsonable_tool_result({2, 1})) == [1, 2]
    assert "RuntimeError" in vendor_mcp._tool_error_text(RuntimeError("bad"), {})
    assert vendor_mcp._unknown_tool_text("missing") == "Unknown tool: missing"


def test_vendor_mcp_run_server_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(vendor_mcp, "run_tool_server", calls.append)
    server = object()
    vendor_mcp.run_server(server)
    assert calls == [server]

    monkeypatch.setattr(vendor_mcp, "create_server", lambda: "created")
    vendor_mcp.run_server()
    assert calls == [server, "created"]

    monkeypatch.setattr(vendor_mcp, "run_server", lambda: calls.append("main"))
    vendor_mcp.main()
    assert calls[-1] == "main"


def install_fake_meshy(monkeypatch: pytest.MonkeyPatch, definitions: list[dict[str, Any]]) -> None:
    """Install provider-owned Meshy tool definitions."""
    package = types.ModuleType("vendor_fabric.meshy")
    tools_module = types.ModuleType("vendor_fabric.meshy.tools")
    tools_module.TOOL_DEFINITIONS = definitions
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy", package)
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy.tools", tools_module)


def test_meshy_mcp_exposes_provider_definitions(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    class Schema:
        @classmethod
        def model_json_schema(cls) -> dict[str, Any]:
            return {
                "properties": {"prompt": {"type": "string"}},
                "required": ["prompt"],
                "$defs": {"unused": {"type": "string"}},
            }

    async def generate(prompt: str) -> dict[str, str]:
        return {"asset": prompt}

    install_fake_meshy(
        monkeypatch,
        [{"name": "generate", "description": "Generate an asset.", "schema": Schema, "func": generate}],
    )
    server = meshy_mcp.create_server()
    listed = asyncio.run(server.on_list_tools(None, None))
    result = asyncio.run(
        server.on_call_tool(None, types.SimpleNamespace(name="generate", arguments={"prompt": "duck"}))
    )

    assert server.name == "meshy-ai"
    assert listed.tools[0].input_schema["type"] == "object"
    assert listed.tools[0].input_schema["$defs"]
    assert result.structured_content == {"asset": "duck"}


def test_meshy_mcp_helper_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    assert meshy_mcp._schema_for_definition({}) == {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }
    assert str(meshy_mcp._install_error("install", ImportError())) == "install"
    assert "detail" in str(meshy_mcp._install_error("install", ImportError("detail")))

    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    assert meshy_mcp._jsonable_tool_result(Dumpable()) == {"dumped": True}
    assert meshy_mcp._jsonable_tool_result([Dumpable()]) == [{"dumped": True}]
    assert sorted(meshy_mcp._jsonable_tool_result({2, 1})) == [1, 2]
    assert "RuntimeError" in meshy_mcp._tool_error_text(RuntimeError("bad"), {})
    assert meshy_mcp._unknown_tool_text("missing") == "Unknown tool: missing"


def test_meshy_mcp_reports_missing_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "vendor_fabric.meshy")
    with pytest.raises(ImportError, match=r"agentic-fabric\[meshy,mcp\]"):
        meshy_mcp._require_meshy_tool_definitions()


def test_meshy_mcp_run_server_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[Any] = []
    monkeypatch.setattr(meshy_mcp, "run_tool_server", calls.append)
    server = object()
    meshy_mcp.run_server(server)
    monkeypatch.setattr(meshy_mcp, "create_server", lambda: "created")
    meshy_mcp.run_server()
    monkeypatch.setattr(meshy_mcp, "run_server", lambda: calls.append("main"))
    meshy_mcp.main()
    assert calls == [server, "created", "main"]
