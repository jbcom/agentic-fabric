"""Tests for configured tool resolution."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from agentic_fabric.tools.registry import resolve_tool, resolve_tools
from agentic_fabric.tools.vendor import VendorCapabilityTool


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

    @patch("agentic_fabric.tools.registry.importlib.import_module")
    def test_resolves_fully_qualified_reference(self, mock_import_module: MagicMock) -> None:
        """module:attribute references should be resolved dynamically."""
        mock_tool_class = MagicMock()
        mock_tool_instance = MagicMock()
        mock_tool_class.return_value = mock_tool_instance

        mock_module = MagicMock()
        mock_module.CustomTool = mock_tool_class
        mock_import_module.return_value = mock_module

        result = resolve_tool("custom.module:CustomTool")

        mock_import_module.assert_called_once_with("custom.module")
        mock_tool_class.assert_called_once_with()
        assert result is mock_tool_instance

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


class TestVendorCapabilityTool:
    """Tests for the generic vendor-backed tool wrapper."""

    def test_runs_operation_through_supplied_data(self) -> None:
        """Supplied data facade should receive provider and kwargs."""
        data = MagicMock()
        data.call.return_value = {"ok": True}
        tool = VendorCapabilityTool("github", "get_file", data=data)

        result = tool(path="README.md")

        assert result == {"ok": True}
        data.call.assert_called_once_with("get_file", "github", path="README.md")
