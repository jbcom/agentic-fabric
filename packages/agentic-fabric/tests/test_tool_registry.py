"""Tests for configured tool resolution."""

from __future__ import annotations

import os

from unittest.mock import MagicMock, patch

import pytest

from agentic_fabric.tools.registry import register_tool_factory, resolve_tool, resolve_tools
from agentic_fabric.tools.vendor import VendorCapabilityTool, vendor_capability_tools


class TestResolveTool:
    """Tests for resolving configured tool names."""

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_resolves_builtin_alias(self, mock_import_module: MagicMock) -> None:
        """FileWriteTool should map to the game code writer implementation."""
        mock_tool_class = MagicMock()
        mock_tool_instance = MagicMock()
        mock_tool_class.return_value = mock_tool_instance

        mock_module = MagicMock()
        mock_module.GameCodeWriterTool = mock_tool_class
        mock_import_module.return_value = mock_module

        result = resolve_tool("FileWriteTool")

        mock_import_module.assert_called_once_with("agentic_fabric.tools.file_tools")
        mock_tool_class.assert_called_once_with()
        assert result is mock_tool_instance

    @patch("agentic_fabric.tools.registry.importlib.import_module", side_effect=ImportError("missing crewai"))
    def test_builtin_alias_skips_missing_optional_dependency(self, mock_import_module: MagicMock) -> None:
        """Built-in aliases should skip cleanly when their optional imports fail."""
        assert resolve_tool("FileWriteTool") is None
        mock_import_module.assert_called_once_with("agentic_fabric.tools.file_tools")

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_resolves_fully_qualified_reference(self, mock_import_module: MagicMock) -> None:
        """Allowed module:attribute references should be resolved dynamically."""
        mock_tool_class = MagicMock()
        mock_tool_instance = MagicMock()
        mock_tool_class.return_value = mock_tool_instance

        mock_module = MagicMock()
        mock_module.CustomTool = mock_tool_class
        mock_import_module.return_value = mock_module

        with patch.dict(os.environ, {"AGENTIC_FABRIC_TOOL_IMPORT_ALLOWLIST": "custom.module"}):
            result = resolve_tool("custom.module:CustomTool")

        mock_import_module.assert_called_once_with("custom.module")
        mock_tool_class.assert_called_once_with()
        assert result is mock_tool_instance

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_skips_unallowed_fully_qualified_reference(self, mock_import_module: MagicMock) -> None:
        """Fully qualified references should require an explicit allowlist."""
        result = resolve_tool("custom.module:CustomTool")

        assert result is None
        mock_import_module.assert_not_called()

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_resolves_allowed_dotted_reference(self, mock_import_module: MagicMock) -> None:
        """Allowed dotted references should resolve module and attribute names."""
        tool = object()
        mock_tool_class = MagicMock(return_value=tool)
        mock_module = MagicMock()
        mock_module.CustomTool = mock_tool_class
        mock_import_module.return_value = mock_module

        result = resolve_tool("agentic_fabric.custom.CustomTool")

        mock_import_module.assert_called_once_with("agentic_fabric.custom")
        assert result is tool

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_skips_unallowed_dotted_reference(self, mock_import_module: MagicMock) -> None:
        """Unallowlisted dotted references should not be imported."""
        result = resolve_tool("external_package.tools.CustomTool")

        assert result is None
        mock_import_module.assert_not_called()

    @pytest.mark.parametrize("side_effect", [ImportError("missing"), AttributeError("missing attr")])
    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_returns_none_when_dynamic_import_fails(self, mock_import_module: MagicMock, side_effect: Exception) -> None:
        """Failed dynamic imports should be skipped cleanly."""
        mock_import_module.side_effect = side_effect

        assert resolve_tool("agentic_fabric.missing:Tool") is None

    def test_resolves_registered_factory_alias(self) -> None:
        """Application code can register safe tool factories directly."""
        tool = object()
        factory = MagicMock(return_value=tool)

        register_tool_factory("UnitTestTool", factory, aliases=("unit-test-tool",))

        assert resolve_tool("unit-test-tool") is tool
        factory.assert_called_once_with()

    def test_returns_none_for_unresolved_mcp_tool(self) -> None:
        """Unsupported MCP tool references should be skipped cleanly."""
        assert resolve_tool("mcp://git/execute_command") is None

    def test_resolves_vendor_uri_tool(self) -> None:
        """Vendor tool URIs should create lazy vendor capability wrappers."""
        tool = resolve_tool("vendor://github/get_file")

        assert isinstance(tool, VendorCapabilityTool)
        assert tool.provider == "github"
        assert tool.operation == "get_file"

    def test_resolves_vendor_colon_tool(self) -> None:
        """Colon-style vendor tool references should also be supported."""
        tool = resolve_tool("vendor:slack:list_messages")

        assert isinstance(tool, VendorCapabilityTool)
        assert tool.provider == "slack"
        assert tool.operation == "list_messages"

    @pytest.mark.parametrize("tool_name", ["vendor://github", "vendor:github"])
    def test_skips_malformed_vendor_tool_references(self, tool_name: str) -> None:
        """Malformed vendor references should behave like unresolved tools."""
        assert resolve_tool(tool_name) is None

    def test_skips_malformed_dotted_reference(self) -> None:
        """Malformed dotted references should resolve to None without importing."""
        assert resolve_tool(".Tool") is None

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_resolve_tools_deduplicates_aliases(self, mock_import_module: MagicMock) -> None:
        """Aliases pointing to the same tool should not instantiate duplicates."""
        mock_tool_class = MagicMock()
        mock_tool_class.return_value = MagicMock()

        mock_module = MagicMock()
        mock_module.GameCodeReaderTool = mock_tool_class
        mock_import_module.return_value = mock_module

        tools = resolve_tools(["FileReadTool", "mcp://filesystem/read_file", "FileReadTool"])

        assert len(tools) == 1
        mock_tool_class.assert_called_once_with()

    def test_resolve_tools_skips_unresolved_unique_names(self) -> None:
        """Unresolved tools should not block later unique tools."""
        tool = object()
        factory = MagicMock(return_value=tool)
        register_tool_factory("UnitTestResolvedTool", factory)

        assert resolve_tools(["mcp://missing/tool", "UnitTestResolvedTool"]) == [tool]


class TestVendorCapabilityTool:
    """Tests for the generic vendor-backed tool wrapper."""

    def test_builds_tool_from_vendor_capability_metadata(self) -> None:
        """VendorData capability metadata should become a lazy tool wrapper."""
        metadata = {
            "provider": "github",
            "operation": "get_file",
            "description": "Read a repository file.",
        }

        tool = VendorCapabilityTool.from_metadata(metadata)

        assert tool.provider == "github"
        assert tool.operation == "get_file"
        assert tool.description == "Read a repository file."
        assert tool.metadata is metadata

    def test_runs_operation_through_supplied_data(self) -> None:
        """Supplied data facade should receive provider and kwargs."""
        data = MagicMock()
        data.call.return_value = {"ok": True}
        tool = VendorCapabilityTool("github", "get_file", data=data)

        result = tool(path="README.md")

        assert result == {"ok": True}
        data.call.assert_called_once_with("get_file", "github", path="README.md")

    def test_runs_operation_through_default_agentic_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Without supplied data, the wrapper should create AgenticData lazily."""
        fake_data = MagicMock()

        class FakeAgenticData:
            def __new__(cls) -> MagicMock:
                return fake_data

        monkeypatch.setattr("agentic_fabric.agentic_data.AgenticData", FakeAgenticData)

        VendorCapabilityTool("github", "get_file")(path="README.md")

        fake_data.call.assert_called_once_with("get_file", "github", path="README.md")

    def test_vendor_capability_tools_reads_vendor_data_catalog(self) -> None:
        """VendorData capabilities should be converted into agent tool wrappers."""
        data = MagicMock()
        data.capabilities.return_value = [
            {"provider": "github", "operation": "get_file", "description": "Read files"},
            {"provider": "", "operation": "broken"},
        ]

        tools = vendor_capability_tools(data, provider="github", include_unavailable=False)

        data.capabilities.assert_called_once_with("github", include_unavailable=False)
        assert len(tools) == 1
        assert tools[0].provider == "github"
        assert tools[0].operation == "get_file"
        assert tools[0].data is data

    def test_vendor_capability_tools_returns_empty_without_vendor_catalog(self) -> None:
        """The import shim should not invent provider behavior."""
        assert vendor_capability_tools(object()) == []
