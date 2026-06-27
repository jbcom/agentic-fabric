"""Tests for MCP transport adapters."""

from __future__ import annotations

import asyncio
import builtins
import sys
import types

from dataclasses import dataclass
from typing import Any

import pytest

from agentic_fabric.tools import meshy_mcp, vendor_mcp


@dataclass
class FakeTextContent:
    type: str
    text: str


class FakeTool:
    def __init__(self, name: str, description: str, inputSchema: dict[str, Any]) -> None:
        self.name = name
        self.description = description
        self.inputSchema = inputSchema


class FakeServer:
    """Minimal MCP server stand-in that records registered handlers."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.list_tools_handler: Any | None = None
        self.call_tool_handler: Any | None = None

    def list_tools(self) -> Any:
        def decorator(func: Any) -> Any:
            self.list_tools_handler = func
            return func

        return decorator

    def call_tool(self) -> Any:
        def decorator(func: Any) -> Any:
            self.call_tool_handler = func
            return func

        return decorator


def install_fake_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install fake MCP modules for adapter tests."""
    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    types_module = types.ModuleType("mcp.types")
    server_module.Server = FakeServer
    types_module.Tool = FakeTool
    types_module.TextContent = FakeTextContent

    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp.types", types_module)


def install_fake_stdio(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, Any, Any]]:
    """Install a fake MCP stdio server and return recorded run calls."""
    calls: list[tuple[Any, Any, Any]] = []

    class FakeStdio:
        async def __aenter__(self) -> tuple[str, str]:
            return ("read", "write")

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            traceback: types.TracebackType | None,
        ) -> bool:
            return False

    stdio_module = types.ModuleType("mcp.server.stdio")
    stdio_module.stdio_server = FakeStdio
    monkeypatch.setitem(sys.modules, "mcp.server.stdio", stdio_module)
    return calls


class RunnableServer:
    def __init__(self, calls: list[tuple[Any, Any, Any]]) -> None:
        self.calls = calls

    def create_initialization_options(self) -> dict[str, bool]:
        return {"ready": True}

    async def run(self, read_stream: Any, write_stream: Any, options: Any) -> None:
        self.calls.append((read_stream, write_stream, options))


def install_fake_extended_data(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install fake extended-data helpers to cover optional success branches."""
    extended_data_module = types.ModuleType("extended_data")
    containers_module = types.ModuleType("extended_data.containers")
    redaction_module = types.ModuleType("extended_data.primitives.redaction")
    io_module = types.ModuleType("extended_data.io")

    containers_module.to_builtin = lambda value: {"converted": value}
    redaction_module.redact_sensitive_data = lambda value: {"redacted": value}
    redaction_module.redact_sensitive_text = lambda value, *, values=None: f"redacted:{value}"
    io_module.wrap_raw_data_for_export = lambda payload, **kwargs: f"wrapped:{payload}:{sorted(kwargs)}"

    monkeypatch.setitem(sys.modules, "extended_data", extended_data_module)
    monkeypatch.setitem(sys.modules, "extended_data.containers", containers_module)
    monkeypatch.setitem(sys.modules, "extended_data.primitives.redaction", redaction_module)
    monkeypatch.setitem(sys.modules, "extended_data.io", io_module)


def reject_imports(monkeypatch: pytest.MonkeyPatch, prefix: str) -> None:
    """Reject imports under a package prefix."""
    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == prefix or name.startswith(f"{prefix}."):
            raise ImportError(f"missing {prefix}")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)


def test_meshy_mcp_reports_missing_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp")

    with pytest.raises(ImportError, match=r"agentic-fabric\[mcp\]"):
        meshy_mcp.create_server()


def test_meshy_mcp_create_tools_reports_missing_mcp_types(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp.types")

    with pytest.raises(ImportError, match=r"agentic-fabric\[mcp\]"):
        meshy_mcp._create_mcp_tools()


def test_meshy_mcp_reports_missing_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    reject_imports(monkeypatch, "vendor_fabric")

    with pytest.raises(ImportError, match=r"vendor-fabric\[meshy\]"):
        meshy_mcp.create_server()


def test_meshy_mcp_exposes_vendor_tool_definitions(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    class FakeSchema:
        @staticmethod
        def model_json_schema() -> dict[str, Any]:
            return {"properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}

    def generate(prompt: str) -> dict[str, str]:
        return {"ok": prompt}

    vendor_module = types.ModuleType("vendor_fabric")
    meshy_module = types.ModuleType("vendor_fabric.meshy")
    tools_module = types.ModuleType("vendor_fabric.meshy.tools")
    tools_module.TOOL_DEFINITIONS = [
        {
            "name": "text3d_generate",
            "description": "Generate a model.",
            "schema": FakeSchema,
            "func": generate,
        }
    ]
    monkeypatch.setitem(sys.modules, "vendor_fabric", vendor_module)
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy", meshy_module)
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy.tools", tools_module)

    server = meshy_mcp.create_server()
    listed = asyncio.run(server.list_tools_handler())
    result = asyncio.run(server.call_tool_handler("text3d_generate", {"prompt": "cube"}))
    unknown = asyncio.run(server.call_tool_handler("missing", None))

    assert server.name == "meshy-ai"
    assert [(tool.name, tool.description, tool.inputSchema) for tool in listed] == [
        (
            "text3d_generate",
            "Generate a model.",
            {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]},
        )
    ]
    assert "cube" in result[0].text
    assert "Unknown tool: missing" in unknown[0].text


def test_meshy_mcp_handles_tool_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)

    def explode(prompt: str) -> dict[str, str]:
        raise RuntimeError(f"failed {prompt}")

    tools_module = types.ModuleType("vendor_fabric.meshy.tools")
    tools_module.TOOL_DEFINITIONS = [{"name": "explode", "schema": None, "func": explode}]
    monkeypatch.setitem(sys.modules, "vendor_fabric", types.ModuleType("vendor_fabric"))
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy", types.ModuleType("vendor_fabric.meshy"))
    monkeypatch.setitem(sys.modules, "vendor_fabric.meshy.tools", tools_module)

    server = meshy_mcp.create_server()
    result = asyncio.run(server.call_tool_handler("explode", {"prompt": "cube"}))

    assert "failed cube" in result[0].text


def test_meshy_mcp_helper_fallbacks(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "extended_data")

    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    assert meshy_mcp._schema_for_definition({}) == {"type": "object", "properties": {}, "required": []}
    assert meshy_mcp._schema_for_definition({"schema": object()}) == {
        "type": "object",
        "properties": {},
        "required": [],
    }
    assert meshy_mcp._to_builtin(Dumpable()) == {"dumped": True}
    assert meshy_mcp._to_builtin([Dumpable()]) == [{"dumped": True}]
    assert meshy_mcp._jsonable_tool_result(Dumpable()) == {"dumped": True}
    assert meshy_mcp._jsonable_tool_result([Dumpable()]) == [{"dumped": True}]
    assert sorted(meshy_mcp._jsonable_tool_result({2, 1})) == [1, 2]

    monkeypatch.setattr(meshy_mcp, "_to_builtin", lambda value: {2, 1} if value == "converted-set" else value)
    assert sorted(meshy_mcp._jsonable_tool_result("converted-set")) == [1, 2]


def test_meshy_mcp_uses_extended_data_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_extended_data(monkeypatch)

    assert meshy_mcp._to_builtin({"value": 1}) == {"converted": {"value": 1}}
    assert meshy_mcp._redact_sensitive_data({"token": "secret"}) == {"redacted": {"token": "secret"}}
    assert meshy_mcp._redact_sensitive_text("secret") == "redacted:secret"
    assert meshy_mcp._tool_payload_text({"ok": True}).startswith("wrapped:")


def test_meshy_mcp_run_server_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    calls = install_fake_stdio(monkeypatch)
    server = RunnableServer(calls)

    meshy_mcp.run_server(server)

    assert calls == [("read", "write", {"ready": True})]

    calls.clear()
    monkeypatch.setattr(meshy_mcp, "create_server", lambda: RunnableServer(calls))

    meshy_mcp.run_server()

    assert calls == [("read", "write", {"ready": True})]

    called: list[bool] = []
    monkeypatch.setattr(meshy_mcp, "run_server", lambda: called.append(True))

    meshy_mcp.main()

    assert called == [True]


def test_meshy_mcp_run_server_reports_missing_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp.server.stdio")

    with pytest.raises(ImportError, match=r"agentic-fabric\[mcp\]"):
        meshy_mcp.run_server(RunnableServer([]))


def install_fake_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> None:
    """Install a fake vendor-fabric registry and data surface."""

    class DemoConnector:
        def search(self, query: str, limit: int = 5) -> dict[str, Any]:
            """Search demo records.

            query: Search text.
            limit: Maximum results.
            """
            return {"query": query, "limit": limit}

        def status(self) -> dict[str, str]:
            return {"status": "ok"}

        async def async_lookup(self) -> dict[str, bool]:
            return {"async": True}

        def fail(self) -> dict[str, bool]:
            raise RuntimeError("connector failed")

    async def list_available_connectors() -> list[str]:
        return ["demo"]

    def list_connector_categories(*, include_unavailable: bool = True) -> list[str]:
        raise RuntimeError("category failed")

    registry = types.SimpleNamespace(
        _list_connector_classes=lambda: {"demo": DemoConnector},
        get_connector=lambda name: DemoConnector(),
        list_connectors=lambda *, include_unavailable=True: ["demo"],
        list_available_connectors=list_available_connectors,
        list_connector_info=lambda *, include_unavailable=True: [{"name": "demo", "available": True}],
        get_connector_info=lambda name, *, include_unavailable=True: {"name": name, "available": True},
        list_connector_categories=list_connector_categories,
        list_connector_capabilities=lambda *, include_unavailable=True: ["search"],
        list_connectors_by_category=lambda category, *, include_unavailable=True: [{"name": "demo", "category": category}],
        list_connectors_by_capability=lambda capability, *, include_unavailable=True: [
            {"name": "demo", "capability": capability}
        ],
    )

    vendor_module = types.ModuleType("vendor_fabric")
    vendor_module.registry = registry
    surface_module = types.ModuleType("vendor_fabric.surface")
    surface_module.connector_data_methods = lambda connector_class: [
        ("close", connector_class.search),
        ("search", connector_class.search),
        ("status", connector_class.status),
        ("async_lookup", connector_class.async_lookup),
        ("fail", connector_class.fail),
    ]

    monkeypatch.setitem(sys.modules, "vendor_fabric", vendor_module)
    monkeypatch.setitem(sys.modules, "vendor_fabric.surface", surface_module)


def test_vendor_mcp_reports_missing_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp")

    with pytest.raises(ImportError, match=r"agentic-fabric\[mcp\]"):
        vendor_mcp.create_server()


def test_vendor_mcp_reports_missing_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    reject_imports(monkeypatch, "vendor_fabric")

    with pytest.raises(ImportError, match="vendor-fabric is required"):
        vendor_mcp.create_server()


def test_vendor_mcp_exposes_catalog_and_connector_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    install_fake_vendor_fabric(monkeypatch)

    server = vendor_mcp.create_server()
    listed = asyncio.run(server.list_tools_handler())
    names = {tool.name for tool in listed}
    catalog_result = asyncio.run(server.call_tool_handler("fabric_vendors_list", None))
    available_result = asyncio.run(server.call_tool_handler("fabric_vendors_list_available", {}))
    category_error = asyncio.run(server.call_tool_handler("fabric_vendors_list_categories", {}))
    connector_result = asyncio.run(server.call_tool_handler("demo_search", {"query": "alpha", "limit": 2}))
    status_result = asyncio.run(server.call_tool_handler("demo_status", {}))
    async_result = asyncio.run(server.call_tool_handler("demo_async_lookup", {}))
    connector_error = asyncio.run(server.call_tool_handler("demo_fail", {}))
    unknown = asyncio.run(server.call_tool_handler("missing", {}))

    assert server.name == "vendor-fabric"
    assert "fabric_vendors_list" in names
    assert "demo_search" in names
    assert "demo" in catalog_result[0].text
    assert "demo" in available_result[0].text
    assert "category failed" in category_error[0].text
    assert "alpha" in connector_result[0].text
    assert "ok" in status_result[0].text
    assert "async" in async_result[0].text
    assert "connector failed" in connector_error[0].text
    assert "Unknown tool: missing" in unknown[0].text


def test_vendor_mcp_helper_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "extended_data")

    class Dumpable:
        def model_dump(self) -> dict[str, bool]:
            return {"dumped": True}

    def typed(
        self: object,
        count: int,
        ratio: float,
        enabled: bool,
        items: list[str],
        payload: dict[str, Any],
        optional: str = "value",
    ) -> dict[str, Any]:
        """Typed method.

        count: Count value.
        """
        return {}

    def unresolved(value: MissingType) -> dict[str, Any]:  # noqa: F821
        return {}

    schema = vendor_mcp._get_method_schema(typed)
    unresolved_schema = vendor_mcp._get_method_schema(unresolved)

    assert schema["properties"]["count"]["type"] == "integer"
    assert schema["properties"]["ratio"]["type"] == "number"
    assert schema["properties"]["enabled"]["type"] == "boolean"
    assert schema["properties"]["items"]["type"] == "array"
    assert schema["properties"]["payload"]["type"] == "object"
    assert schema["properties"]["optional"]["default"] == "value"
    assert schema["properties"]["count"]["description"] == "Count value."
    assert unresolved_schema["properties"]["value"]["type"] == "string"
    assert vendor_mcp._connector_classes(types.SimpleNamespace()) == {}
    assert vendor_mcp._to_builtin(Dumpable()) == {"dumped": True}
    assert vendor_mcp._to_builtin([Dumpable()]) == [{"dumped": True}]
    assert vendor_mcp._jsonable_tool_result(Dumpable()) == {"dumped": True}
    assert vendor_mcp._jsonable_tool_result([Dumpable()]) == [{"dumped": True}]
    assert sorted(vendor_mcp._jsonable_tool_result({2, 1})) == [1, 2]

    monkeypatch.setattr(vendor_mcp, "_to_builtin", lambda value: {2, 1} if value == "converted-set" else value)
    assert sorted(vendor_mcp._jsonable_tool_result("converted-set")) == [1, 2]


def test_vendor_mcp_uses_extended_data_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_extended_data(monkeypatch)

    assert vendor_mcp._to_builtin({"value": 1}) == {"converted": {"value": 1}}
    assert vendor_mcp._redact_sensitive_data({"token": "secret"}) == {"redacted": {"token": "secret"}}
    assert vendor_mcp._tool_error_text(RuntimeError("secret")) == "Error: RuntimeError: redacted:secret"
    assert vendor_mcp._unknown_tool_text("secret") == "Unknown tool: redacted:secret"
    assert vendor_mcp._tool_result_text({"ok": True}).startswith("wrapped:")


def test_vendor_mcp_run_server_and_main(monkeypatch: pytest.MonkeyPatch) -> None:
    install_fake_mcp(monkeypatch)
    install_fake_vendor_fabric(monkeypatch)
    calls = install_fake_stdio(monkeypatch)
    server = RunnableServer(calls)

    vendor_mcp.run_server(server)

    assert calls == [("read", "write", {"ready": True})]

    calls.clear()
    monkeypatch.setattr(vendor_mcp, "create_server", lambda: RunnableServer(calls))

    vendor_mcp.run_server()

    assert calls == [("read", "write", {"ready": True})]

    called: list[bool] = []
    monkeypatch.setattr(vendor_mcp, "run_server", lambda: called.append(True))

    vendor_mcp.main()

    assert called == [True]


def test_vendor_mcp_run_server_reports_missing_stdio(monkeypatch: pytest.MonkeyPatch) -> None:
    reject_imports(monkeypatch, "mcp.server.stdio")

    with pytest.raises(ImportError, match=r"agentic-fabric\[mcp\]"):
        vendor_mcp.run_server(RunnableServer([]))
