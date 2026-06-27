"""Tests for AgenticData runtime context and dispatch."""

from __future__ import annotations

import importlib.util
import sys
import types

from pathlib import Path
from typing import Any

import pytest

from agentic_fabric import AgenticData
from agentic_fabric.runners.registry import RuntimeUnavailableError


def test_agentic_data_preserves_value_and_runtime_context(monkeypatch: pytest.MonkeyPatch) -> None:
    """AgenticData should keep data and active runtime context together."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "langgraph")

    data = AgenticData({"task": "summarize"})
    data.use_runtime("langgraph")
    data.cast({"task": "rewrite"})

    assert data.active_runtime == "langgraph"
    assert data.as_builtin() == {"task": "rewrite"}


def test_use_runtime_strict_reports_install_guidance(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable runtimes should raise a typed error with install guidance."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: False)

    with pytest.raises(RuntimeUnavailableError, match="pip install crewai"):
        AgenticData().use_runtime("crewai")


def test_select_runtime_prefers_explicit_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit runtime selection should override an active runtime."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "strands")

    data = AgenticData(active_runtime="langgraph")

    assert data.select_runtime("strands") == "strands"


def test_select_runtime_rejects_active_manifest_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Active runtime and required manifest runtime should not silently conflict."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    data = AgenticData(active_runtime="langgraph")

    with pytest.raises(ValueError, match="conflicts"):
        data.select_runtime(fabric_agent_config={"required_framework": "crewai"})


def test_select_runtime_uses_active_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """An active runtime should be selected when no explicit runtime is requested."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "strands")
    data = AgenticData(active_runtime="strands")

    assert data.select_runtime() == "strands"


def test_run_fabric_agent_uses_registered_config_and_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Named fabric agents should route through run_fabric_agent_auto with merged inputs."""
    calls: list[tuple[dict[str, Any], dict[str, Any], str | None]] = []

    def fake_run_fabric_agent_auto(fabric_agent_config: dict[str, Any], inputs: dict[str, Any], framework: str | None = None) -> str:
        calls.append((fabric_agent_config, inputs, framework))
        return "done"

    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "crewai")
    monkeypatch.setattr("agentic_fabric.core.decomposer.run_fabric_agent_auto", fake_run_fabric_agent_auto)

    data = AgenticData(fabric_agents={"reviewer": {"name": "review", "agents": {}, "tasks": {}}})

    result = data.run_reviewer({"code": "x"}, severity="high")

    assert result == "done"
    assert calls == [({"name": "review", "agents": {}, "tasks": {}}, {"code": "x", "severity": "high"}, "crewai")]


def test_unknown_fabric_agent_lists_registered_names() -> None:
    """Unknown fabric agent errors should include the registered names."""
    data = AgenticData(fabric_agents={"reviewer": {"name": "review"}})

    with pytest.raises(KeyError, match="reviewer"):
        data.run_fabric_agent("writer")


def test_fallback_vendor_guidance_when_vendor_fabric_missing() -> None:
    """The no-vendor fallback should fail with install guidance."""
    data = AgenticData()
    if data.vendor_fabric_available:
        pytest.skip("vendor-fabric is installed in this environment")

    with pytest.raises(ImportError, match="vendor-fabric"):
        data.open("github")


def test_fallback_vendor_records_provider_when_not_strict() -> None:
    """The no-vendor fallback should still keep non-strict provider context."""
    data = AgenticData()
    if data.vendor_fabric_available:
        pytest.skip("vendor-fabric is installed in this environment")

    assert data.open("github", strict=False) is data
    assert data.active_provider == "github"

    with pytest.raises(ImportError, match="Vendor operation 'sync' requires vendor-fabric"):
        data.call("sync")


def test_agentic_data_import_branch_with_vendor_fabric(monkeypatch: pytest.MonkeyPatch) -> None:
    """The module should subclass real VendorData when vendor-fabric is importable."""
    import agentic_fabric.agentic_data as current_agentic_data

    fake_vendor_fabric = types.ModuleType("vendor_fabric")
    fake_vendor_data = types.ModuleType("vendor_fabric.vendor_data")

    class VendorData:
        def __init__(self, value: Any = None, **_: Any) -> None:
            self.value = value

        def cast(self, value: Any) -> VendorData:
            self.value = value
            return self

    fake_vendor_data.VendorData = VendorData
    monkeypatch.setitem(sys.modules, "vendor_fabric", fake_vendor_fabric)
    monkeypatch.setitem(sys.modules, "vendor_fabric.vendor_data", fake_vendor_data)

    spec = importlib.util.spec_from_file_location(
        "_agentic_data_vendor_branch",
        Path(current_agentic_data.__file__),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = module.AgenticData("value")

    assert module._VENDOR_FABRIC_AVAILABLE is True
    assert data.vendor_fabric_available is True
    assert isinstance(data, VendorData)
    assert data.value == "value"


def test_fabric_agents_are_read_only_and_unregister_is_chainable() -> None:
    """Fabric agent registry snapshots should be immutable from the public property."""
    data = AgenticData(fabric_agents={"reviewer": {"name": "review"}})

    with pytest.raises(TypeError):
        data.fabric_agents["writer"] = {"name": "write"}  # type: ignore[index]

    assert data.unregister_fabric_agent("reviewer") is data
    assert data.fabric_agents == {}
    assert data.unregister_fabric_agent("missing") is data


def test_use_runtime_auto_and_clear_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """The auto runtime token should select a concrete runtime and clear cleanly."""
    monkeypatch.setattr(AgenticData, "select_runtime", lambda self: "crewai")

    data = AgenticData().use_runtime(" auto ", strict=False)

    assert data.active_runtime == "crewai"
    assert data.clear_runtime() is data
    assert data.active_runtime is None


def test_runtime_metadata_methods_delegate_to_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runtime metadata helpers should normalize registry responses."""
    monkeypatch.setattr(
        "agentic_fabric.agentic_data.runtime_info",
        lambda runtime=None: {"name": runtime or "crewai", "available": True},
    )

    data = AgenticData()

    assert data.runtimes() == [{"name": "crewai", "available": True}]
    assert data.runtime_info("langgraph") == {"name": "langgraph", "available": True}


def test_select_runtime_rejects_explicit_manifest_conflict(monkeypatch: pytest.MonkeyPatch) -> None:
    """Explicit runtime and manifest runtime requirements should agree."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    data = AgenticData()

    with pytest.raises(ValueError, match="Fabric agent requires crewai but langgraph was requested"):
        data.select_runtime("langgraph", fabric_agent_config={"runtime": "crewai"})


def test_select_runtime_uses_required_runtime_and_auto_detection(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manifest requirements should win before auto-detection fallback."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    monkeypatch.setattr("agentic_fabric.core.decomposer.detect_framework", lambda: "strands")
    data = AgenticData()

    assert data.select_runtime(fabric_agent_config={"framework": "langgraph"}) == "langgraph"
    assert data.select_runtime() == "strands"


def test_select_runtime_reports_unavailable_requested_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    """Unavailable explicit runtimes should raise install guidance."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: False)

    with pytest.raises(RuntimeUnavailableError, match="pip install crewai"):
        AgenticData().select_runtime("crewai")


def test_run_fabric_agent_accepts_direct_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    """Direct fabric agent config mappings should bypass registry lookup."""
    calls: list[tuple[dict[str, Any], dict[str, Any], str | None]] = []

    def fake_run_fabric_agent_auto(fabric_agent_config: dict[str, Any], inputs: dict[str, Any], framework: str | None = None) -> str:
        calls.append((fabric_agent_config, inputs, framework))
        return "done"

    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: runtime == "crewai")
    monkeypatch.setattr("agentic_fabric.core.decomposer.run_fabric_agent_auto", fake_run_fabric_agent_auto)

    result = AgenticData().run_fabric_agent({"name": "direct", "runtime": "crewai"}, {"a": 1}, b=2)

    assert result == "done"
    assert calls == [({"name": "direct", "runtime": "crewai"}, {"a": 1, "b": 2}, "crewai")]


def test_call_runtime_delegates_to_selected_runner(monkeypatch: pytest.MonkeyPatch) -> None:
    """Runtime capability calls should use the selected runner."""

    class FakeRunner:
        def call_capability(self, capability: str, *args: Any, **kwargs: Any) -> tuple[Any, ...]:
            return (capability, args, kwargs)

    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    monkeypatch.setattr("agentic_fabric.core.decomposer.get_runner", lambda runtime: FakeRunner())

    assert AgenticData().call_runtime("run", 1, runtime="crewai", flag=True) == ("run", (1,), {"flag": True})


def test_vendor_tools_delegate_to_vendor_capability_catalog(monkeypatch: pytest.MonkeyPatch) -> None:
    """AgenticData should expose agent-facing tools from vendor capabilities."""
    calls: list[tuple[AgenticData, str | None, bool]] = []

    def fake_vendor_capability_tools(
        data: AgenticData,
        *,
        provider: str | None = None,
        include_unavailable: bool = True,
    ) -> list[str]:
        calls.append((data, provider, include_unavailable))
        return ["tool"]

    monkeypatch.setattr("agentic_fabric.tools.vendor.vendor_capability_tools", fake_vendor_capability_tools)

    data = AgenticData()

    assert data.vendor_tools("github", include_unavailable=False) == ["tool"]
    assert calls == [(data, "github", False)]


def test_dynamic_helpers_and_missing_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Registered fabric agents should appear as dynamic run_<fabric_agent> helpers."""
    monkeypatch.setattr("agentic_fabric.core.decomposer.is_framework_available", lambda runtime: True)
    monkeypatch.setattr("agentic_fabric.core.decomposer.run_fabric_agent_auto", lambda fabric_agent_config, inputs, framework: "done")

    data = AgenticData(fabric_agents={"reviewer": {"name": "reviewer", "runtime": "crewai"}})

    assert "run_reviewer" in dir(data)
    assert data.run_reviewer() == "done"

    with pytest.raises(AttributeError, match="has no attribute 'missing'"):
        data.missing


def test_fallback_vendor_data_base_capabilities_returns_empty_list() -> None:
    """The no-vendor fallback should expose an empty capabilities list."""
    data = AgenticData()
    if data.vendor_fabric_available:
        pytest.skip("vendor-fabric is installed in this environment")

    assert data.capabilities() == []
    assert data.capabilities("github", include_unavailable=False) == []


def test_agentic_data_delegates_to_vendor_data_getattr(monkeypatch: pytest.MonkeyPatch) -> None:
    """When the real VendorData defines __getattr__, AgenticData should delegate to it."""
    import agentic_fabric.agentic_data as current_agentic_data

    fake_vendor_fabric = types.ModuleType("vendor_fabric")
    fake_vendor_data = types.ModuleType("vendor_fabric.vendor_data")

    class VendorDataWithGetattr:
        def __init__(self, value: Any = None, **_: Any) -> None:
            self.value = value

        def __getattr__(self, name: str) -> Any:
            if name == "dispatched_provider":
                return "vendor-dispatched"
            raise AttributeError(f"VendorData has no attribute {name!r}")

    fake_vendor_data.VendorData = VendorDataWithGetattr
    monkeypatch.setitem(sys.modules, "vendor_fabric", fake_vendor_fabric)
    monkeypatch.setitem(sys.modules, "vendor_fabric.vendor_data", fake_vendor_data)

    spec = importlib.util.spec_from_file_location(
        "_agentic_data_getattr_delegation",
        Path(current_agentic_data.__file__),
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    data = module.AgenticData("value")

    assert data.dispatched_provider == "vendor-dispatched"
