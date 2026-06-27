"""Agent runtime facade over the vendor and data layers."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Any, ClassVar

from agentic_fabric.runners.registry import RuntimeUnavailableError, install_command, runtime_info, runtime_names


try:  # pragma: no cover - exercised when vendor-fabric is installed by consumers
    from vendor_fabric.vendor_data import VendorData as _VendorDataBase
except ImportError:  # pragma: no cover - default in this workspace until vendor-fabric is published
    _VENDOR_FABRIC_AVAILABLE = False

    class _VendorDataBase:  # type: ignore[no-redef]
        """Small fallback that keeps AgenticData importable without vendor-fabric."""

        def __init__(self, value: Any = None, **_: Any) -> None:
            self._agentic_value = value
            self._active_provider: str | None = None

        @property
        def value(self) -> Any:
            """Return the wrapped value."""
            return self._agentic_value

        @property
        def active_provider(self) -> str | None:
            """Return the active vendor provider, when available."""
            return self._active_provider

        def as_builtin(self) -> Any:
            """Return the wrapped value unchanged."""
            return self._agentic_value

        def cast(self, value: Any) -> _VendorDataBase:
            """Replace the wrapped value."""
            self._agentic_value = value
            return self

        def open(self, provider_id: str, *, strict: bool = True, **_: Any) -> _VendorDataBase:
            """Record a provider or raise install guidance when strict."""
            if strict:
                msg = (
                    f"Provider '{provider_id}' requires vendor-fabric. "
                    "Install vendor-fabric after it is published, then reinstall agentic-fabric."
                )
                raise ImportError(msg)
            self._active_provider = provider_id
            return self

        def call(self, operation: str, *_: Any, **__: Any) -> Any:
            """Raise clear guidance for vendor-backed operations."""
            msg = f"Vendor operation '{operation}' requires vendor-fabric."
            raise ImportError(msg)

else:
    _VENDOR_FABRIC_AVAILABLE = True


class AgenticData(_VendorDataBase):
    """VendorData extension with active runtime and fabric agent registry context."""

    runtime_priority: ClassVar[tuple[str, ...]] = tuple(runtime_names())

    def __init__(
        self,
        value: Any = None,
        *,
        fabric: Any | None = None,
        fabric_agents: Mapping[str, Mapping[str, Any]] | None = None,
        logger: Any | None = None,
        active_runtime: str | None = None,
        **fabric_kwargs: Any,
    ) -> None:
        """Initialize data, registered fabric agents, and optional active runtime."""
        super().__init__(value, fabric=fabric, logger=logger, **fabric_kwargs)
        self._fabric_agents: dict[str, dict[str, Any]] = {
            name: dict(config) for name, config in (fabric_agents or {}).items()
        }
        self._active_runtime: str | None = None
        if active_runtime is not None:
            self.use_runtime(active_runtime, strict=False)

    @property
    def fabric_agents(self) -> Mapping[str, Mapping[str, Any]]:
        """Return registered fabric agent definitions."""
        return MappingProxyType(self._fabric_agents)

    @property
    def active_runtime(self) -> str | None:
        """Return the active runtime name, when one has been selected."""
        return self._active_runtime

    @property
    def vendor_fabric_available(self) -> bool:
        """Return whether this import is backed by a real VendorData class."""
        return _VENDOR_FABRIC_AVAILABLE

    def cast(self, value: Any) -> AgenticData:
        """Mutate the wrapped data while preserving runtime context."""
        super().cast(value)
        return self

    def register_fabric_agent(self, name: str, fabric_agent_config: Mapping[str, Any]) -> AgenticData:
        """Register a named fabric agent config for ``run_fabric_agent`` lookup."""
        self._fabric_agents[name] = dict(fabric_agent_config)
        return self

    def unregister_fabric_agent(self, name: str) -> AgenticData:
        """Remove a named fabric agent config if it exists."""
        self._fabric_agents.pop(name, None)
        return self

    def use_runtime(self, runtime: str, *, strict: bool = True) -> AgenticData:
        """Select the active runtime for future agent calls."""
        normalized = runtime.strip().lower()
        if normalized == "auto":
            normalized = self.select_runtime()
        if strict and not self.is_runtime_available(normalized):
            raise RuntimeUnavailableError(normalized, install_command(normalized))
        self._active_runtime = normalized
        return self

    def clear_runtime(self) -> AgenticData:
        """Clear the active runtime selection."""
        self._active_runtime = None
        return self

    def runtimes(self) -> list[dict[str, Any]]:
        """Return runtime registry metadata with availability."""
        info = runtime_info()
        return list(info) if isinstance(info, list) else [info]

    def runtime_info(self, runtime: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
        """Return runtime metadata with current availability."""
        return runtime_info(runtime)

    def is_runtime_available(self, runtime: str) -> bool:
        """Return whether a runtime is importable in the current environment."""
        from agentic_fabric.core.decomposer import is_framework_available

        return is_framework_available(runtime)

    def select_runtime(
        self,
        runtime: str | None = None,
        *,
        fabric_agent_config: Mapping[str, Any] | None = None,
    ) -> str:
        """Select a runtime using explicit, active, manifest, then auto priority."""
        required_runtime = _manifest_runtime(fabric_agent_config)
        requested = _normalize_runtime(runtime)
        active = _normalize_runtime(self._active_runtime)

        if requested is not None and required_runtime is not None and requested != required_runtime:
            msg = f"Fabric agent requires {required_runtime} but {requested} was requested"
            raise ValueError(msg)

        if requested is not None:
            return _require_available(requested)

        if active is not None:
            if required_runtime is not None and active != required_runtime:
                msg = f"Active runtime {active} conflicts with fabric agent requirement {required_runtime}"
                raise ValueError(msg)
            return _require_available(active)

        if required_runtime is not None:
            return _require_available(required_runtime)

        from agentic_fabric.core.decomposer import detect_framework

        return detect_framework()

    def run_fabric_agent(
        self,
        fabric_agent: str | Mapping[str, Any],
        inputs: Mapping[str, Any] | None = None,
        *,
        runtime: str | None = None,
        **input_kwargs: Any,
    ) -> str:
        """Run a registered fabric agent by name or a direct fabric agent config."""
        from agentic_fabric.core.decomposer import run_fabric_agent_auto

        fabric_agent_config = self._lookup_fabric_agent(fabric_agent)
        merged_inputs = dict(inputs or {})
        merged_inputs.update(input_kwargs)
        selected_runtime = self.select_runtime(runtime, fabric_agent_config=fabric_agent_config)
        return run_fabric_agent_auto(fabric_agent_config, inputs=merged_inputs, framework=selected_runtime)

    def call_runtime(self, capability: str, *args: Any, runtime: str | None = None, **kwargs: Any) -> Any:
        """Call a declared capability on a selected runtime runner."""
        from agentic_fabric.core.decomposer import get_runner

        selected_runtime = self.select_runtime(runtime)
        runner = get_runner(selected_runtime)
        return runner.call_capability(capability, *args, **kwargs)

    def vendor_tools(
        self,
        provider: str | None = None,
        *,
        include_unavailable: bool = True,
    ) -> list[Any]:
        """Return agent-facing tools built from inherited vendor capabilities."""
        from agentic_fabric.tools.vendor import vendor_capability_tools

        return vendor_capability_tools(self, provider=provider, include_unavailable=include_unavailable)

    def __getattr__(self, name: str) -> Any:
        """Expose ``run_<fabric_agent>`` helpers while preserving VendorData dispatch."""
        if name.startswith("run_"):
            fabric_agent_name = name.removeprefix("run_")
            if fabric_agent_name in self._fabric_agents:
                return lambda *args, **kwargs: self.run_fabric_agent(fabric_agent_name, *args, **kwargs)

        try:
            return super().__getattr__(name)  # type: ignore[misc]
        except AttributeError:
            raise AttributeError(f"{type(self).__name__!s} has no attribute {name!r}") from None

    def __dir__(self) -> list[str]:
        """Include dynamic registered-fabric-agent helpers in introspection."""
        dynamic = [f"run_{name}" for name in self._fabric_agents]
        return sorted({*super().__dir__(), *dynamic})

    def _lookup_fabric_agent(self, fabric_agent: str | Mapping[str, Any]) -> dict[str, Any]:
        """Return a fabric agent config from a name or direct mapping."""
        if isinstance(fabric_agent, Mapping):
            return dict(fabric_agent)
        try:
            return dict(self._fabric_agents[fabric_agent])
        except KeyError as exc:
            options = ", ".join(sorted(self._fabric_agents)) or "none registered"
            msg = f"Unknown fabric agent '{fabric_agent}'. Registered fabric agents: {options}"
            raise KeyError(msg) from exc


def _normalize_runtime(runtime: str | None) -> str | None:
    """Normalize runtime names and treat auto as no explicit choice."""
    if runtime is None:
        return None
    normalized = runtime.strip().lower()
    return None if normalized == "auto" else normalized


def _manifest_runtime(fabric_agent_config: Mapping[str, Any] | None) -> str | None:
    """Read runtime requirements from a fabric agent manifest/config mapping."""
    if fabric_agent_config is None:
        return None
    runtime = fabric_agent_config.get("required_framework") or fabric_agent_config.get("runtime") or fabric_agent_config.get("framework")
    return _normalize_runtime(str(runtime)) if runtime else None


def _require_available(runtime: str) -> str:
    """Return a runtime or raise install guidance."""
    from agentic_fabric.core.decomposer import is_framework_available

    if not is_framework_available(runtime):
        raise RuntimeUnavailableError(runtime, install_command(runtime))
    return runtime
