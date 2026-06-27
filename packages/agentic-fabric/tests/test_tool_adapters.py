"""Tests for framework-specific configured tool adapters."""

from __future__ import annotations

import sys

from types import ModuleType, SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from agentic_fabric.tools.adapters import (
    _build_runner,
    _invoke_tool,
    _tool_name,
    resolve_langgraph_tools,
    resolve_strands_tools,
)


class WriteFileArgs:
    """Schema used to verify adapter schema forwarding."""

    @classmethod
    def model_json_schema(cls) -> dict[str, str]:
        """Return a minimal schema compatible with adapter expectations."""
        return {"title": "WriteFileArgs"}


class DummyTool:
    """Simple tool object with a CrewAI-style `_run` entrypoint."""

    name = "Write Game Code File"
    description = "Write code into the workspace."
    args_schema = WriteFileArgs

    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def _run(self, **kwargs: str) -> str:
        self.calls.append(kwargs)
        return f"wrote:{kwargs['file_path']}"


class CallableTool:
    """Callable tool object without a CrewAI _run method."""

    __name__ = "1 callable tool"

    def __call__(self, **kwargs: str) -> str:
        return f"called:{kwargs['value']}"


class SignatureTool:
    """Tool without args_schema whose _run signature should be preserved."""

    name = "signature_tool"
    description = "Uses signature inference."

    def _run(self, file_path: str, mode: str = "r") -> str:
        return f"{mode}:{file_path}"


class FakeStructuredTool:
    """Minimal LangChain-style tool wrapper used for adapter tests."""

    def __init__(
        self,
        *,
        func,
        name: str,
        description: str,
        args_schema: type[WriteFileArgs] | None,
        infer_schema: bool,
    ) -> None:
        self.func = func
        self.name = name
        self.description = description
        self.args_schema = args_schema
        self.infer_schema = infer_schema

    @classmethod
    def from_function(
        cls,
        *,
        func,
        name: str,
        description: str,
        args_schema: type[WriteFileArgs] | None,
        infer_schema: bool,
    ) -> FakeStructuredTool:
        return cls(
            func=func,
            name=name,
            description=description,
            args_schema=args_schema,
            infer_schema=infer_schema,
        )

    def invoke(self, kwargs: dict[str, str]) -> str:
        return self.func(**kwargs)


def fake_strands_tool(*, name: str, description: str, inputSchema: dict | None):
    """Minimal Strands decorator used for adapter tests."""

    def decorator(func):
        def wrapped(**kwargs: str) -> str:
            return func(**kwargs)

        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        wrapped.TOOL_SPEC = {
            "name": name,
            "description": description,
            "inputSchema": inputSchema,
        }
        return wrapped

    return decorator


class TestLangGraphToolAdapters:
    """Tests for LangGraph configured-tool wrapping."""

    def test_empty_and_unresolved_tools_return_empty(self) -> None:
        """Empty declarations and unresolved names should not require LangChain."""
        assert resolve_langgraph_tools([]) == []

        with patch("agentic_fabric.tools.adapters.resolve_tools", return_value=[]):
            assert resolve_langgraph_tools(["missing"]) == []

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_missing_langchain_dependency_raises(self, mock_resolve_tools: MagicMock) -> None:
        """Missing LangChain should raise RuntimeError instead of silently returning empty."""
        mock_resolve_tools.return_value = [DummyTool()]

        with patch.dict(sys.modules, {"langchain_core.tools": None}):
            with pytest.raises(RuntimeError, match="LangGraph tool adaptation unavailable"):
                resolve_langgraph_tools(["FileWriteTool"])

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_wraps_resolved_tools_with_structured_tool(self, mock_resolve_tools: MagicMock) -> None:
        """Resolved tools should be adapted into LangChain-compatible wrappers."""
        tool = DummyTool()
        mock_resolve_tools.return_value = [tool]

        fake_tools_module = ModuleType("langchain_core.tools")
        fake_tools_module.StructuredTool = FakeStructuredTool

        with patch.dict(sys.modules, {"langchain_core.tools": fake_tools_module}):
            adapted = resolve_langgraph_tools(["FileWriteTool"])

        assert len(adapted) == 1
        wrapped = adapted[0]
        assert wrapped.name == "Write_Game_Code_File"
        assert wrapped.description == "Write code into the workspace."
        assert wrapped.args_schema is WriteFileArgs
        assert wrapped.infer_schema is False
        assert wrapped.invoke({"file_path": "src/game.ts"}) == "wrote:src/game.ts"
        assert tool.calls == [{"file_path": "src/game.ts"}]

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_preserves_existing_langgraph_tool_objects(self, mock_resolve_tools: MagicMock) -> None:
        """Existing invoke-capable tools should pass through unchanged."""
        existing_tool = SimpleNamespace(name="get_magic_number", invoke=MagicMock(return_value=42))
        mock_resolve_tools.return_value = [existing_tool]

        fake_tools_module = ModuleType("langchain_core.tools")
        fake_tools_module.StructuredTool = FakeStructuredTool

        with patch.dict(sys.modules, {"langchain_core.tools": fake_tools_module}):
            adapted = resolve_langgraph_tools(["get_magic_number"])

        assert adapted == [existing_tool]

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_preserves_runner_signature_for_schema_inference(self, mock_resolve_tools: MagicMock) -> None:
        """LangChain schema inference should see the wrapped tool's real arguments."""
        mock_resolve_tools.return_value = [SignatureTool()]

        fake_tools_module = ModuleType("langchain_core.tools")
        fake_tools_module.StructuredTool = FakeStructuredTool

        with patch.dict(sys.modules, {"langchain_core.tools": fake_tools_module}):
            adapted = resolve_langgraph_tools(["SignatureTool"])

        wrapped = adapted[0]
        assert wrapped.infer_schema is True
        assert tuple(wrapped.func.__signature__.parameters) == ("file_path", "mode")


class TestStrandsToolAdapters:
    """Tests for Strands configured-tool wrapping."""

    def test_empty_and_unresolved_tools_return_empty(self) -> None:
        """Empty declarations and unresolved names should not require Strands."""
        assert resolve_strands_tools([]) == []

        with patch("agentic_fabric.tools.adapters.resolve_tools", return_value=[]):
            assert resolve_strands_tools(["missing"]) == []

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_missing_strands_dependency_raises(self, mock_resolve_tools: MagicMock) -> None:
        """Missing Strands should raise RuntimeError instead of silently returning empty."""
        mock_resolve_tools.return_value = [DummyTool()]

        with patch.dict(sys.modules, {"strands": None}):
            with pytest.raises(RuntimeError, match="Strands tool adaptation unavailable"):
                resolve_strands_tools(["FileWriteTool"])

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_wraps_resolved_tools_with_strands_decorator(self, mock_resolve_tools: MagicMock) -> None:
        """Resolved tools should be adapted into callable Strands tool wrappers."""
        tool = DummyTool()
        mock_resolve_tools.return_value = [tool]

        fake_strands_module = ModuleType("strands")
        fake_strands_module.tool = fake_strands_tool

        with patch.dict(sys.modules, {"strands": fake_strands_module}):
            adapted = resolve_strands_tools(["FileWriteTool"])

        assert len(adapted) == 1
        wrapped = adapted[0]
        assert wrapped(file_path="src/game.ts") == "wrote:src/game.ts"
        assert tool.calls == [{"file_path": "src/game.ts"}]
        assert wrapped.TOOL_SPEC["name"] == "Write_Game_Code_File"
        assert wrapped.TOOL_SPEC["description"] == "Write code into the workspace."
        assert wrapped.TOOL_SPEC["inputSchema"] == WriteFileArgs.model_json_schema()

    @patch("agentic_fabric.tools.adapters.resolve_tools")
    def test_preserves_existing_strands_tool_objects(self, mock_resolve_tools: MagicMock) -> None:
        """Existing Strands tool objects should pass through unchanged."""
        existing_tool = SimpleNamespace(TOOL_SPEC={"name": "get_secret_number"})
        mock_resolve_tools.return_value = [existing_tool]

        fake_strands_module = ModuleType("strands")
        fake_strands_module.tool = fake_strands_tool

        with patch.dict(sys.modules, {"strands": fake_strands_module}):
            adapted = resolve_strands_tools(["get_secret_number"])

        assert adapted == [existing_tool]


class TestToolAdapterHelpers:
    """Tests for plain adapter helper functions."""

    def test_tool_names_are_framework_safe(self) -> None:
        assert _tool_name(CallableTool()) == "tool_1_callable_tool"
        assert _tool_name(object()) == "object"

    def test_build_runner_invokes_callable_tools(self) -> None:
        runner = _build_runner(CallableTool(), "callable_tool", "Call a tool.")

        assert runner(value="x") == "called:x"
        assert runner.__name__ == "callable_tool"
        assert runner.__doc__ == "Call a tool."

    def test_build_runner_preserves_tool_signature(self) -> None:
        runner = _build_runner(SignatureTool(), "signature_tool", "Uses signature inference.")

        assert runner(file_path="README.md", mode="rb") == "rb:README.md"
        assert tuple(runner.__signature__.parameters) == ("file_path", "mode")

    def test_invoke_tool_rejects_noncallable_objects(self) -> None:
        with pytest.raises(TypeError, match="not callable"):
            _invoke_tool(object(), {})
