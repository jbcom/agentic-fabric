"""Lazy runtime registry for optional agent frameworks."""

from __future__ import annotations

import importlib

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class RuntimeSpec:
    """Metadata required to discover and instantiate one runtime."""

    name: str
    import_name: str
    runner_module: str
    runner_class: str
    install: str
    extra: str | None
    description: str = ""

    def as_dict(self, *, available: bool) -> dict[str, Any]:
        """Return serializable runtime metadata."""
        return {
            "name": self.name,
            "import_name": self.import_name,
            "runner": f"{self.runner_module}:{self.runner_class}",
            "install": self.install,
            "extra": self.extra,
            "available": available,
            "description": self.description,
        }


class RuntimeUnavailableError(RuntimeError):
    """Raised when an optional runtime cannot be selected."""

    def __init__(self, runtime: str, install: str) -> None:
        """Initialize the error with runtime-specific install guidance."""
        super().__init__(f"Runtime '{runtime}' is not available. Install with: {install}")
        self.runtime = runtime
        self.install = install


_RUNTIME_SPECS: dict[str, RuntimeSpec] = {}
_AVAILABILITY_CACHE: dict[str, bool] = {}


def register_runtime(spec: RuntimeSpec) -> None:
    """Register or replace one runtime spec."""
    _RUNTIME_SPECS[spec.name] = spec
    _AVAILABILITY_CACHE.pop(spec.name, None)


def runtime_specs() -> MappingProxyType[str, RuntimeSpec]:
    """Return registered runtime specs in priority order."""
    return MappingProxyType(_RUNTIME_SPECS)


def runtime_names() -> list[str]:
    """Return registered runtime names in priority order."""
    return list(_RUNTIME_SPECS)


def get_runtime_spec(runtime: str) -> RuntimeSpec:
    """Return a registered runtime spec."""
    try:
        return _RUNTIME_SPECS[runtime]
    except KeyError as exc:
        options = ", ".join(runtime_names())
        msg = f"Unknown runtime: {runtime}. Options: [{options}]"
        raise ValueError(msg) from exc


def clear_runtime_cache() -> None:
    """Clear cached optional-runtime availability."""
    _AVAILABILITY_CACHE.clear()


def is_runtime_available(runtime: str) -> bool:
    """Return whether a runtime import target is importable."""
    if runtime in _AVAILABILITY_CACHE:
        return _AVAILABILITY_CACHE[runtime]
    if runtime not in _RUNTIME_SPECS:
        _AVAILABILITY_CACHE[runtime] = False
        return False

    try:
        importlib.import_module(_RUNTIME_SPECS[runtime].import_name)
    except ImportError:
        _AVAILABILITY_CACHE[runtime] = False
    else:
        _AVAILABILITY_CACHE[runtime] = True
    return _AVAILABILITY_CACHE[runtime]


def available_runtimes() -> list[str]:
    """Return available runtime names in priority order."""
    return [runtime for runtime in runtime_names() if is_runtime_available(runtime)]


def runtime_info(runtime: str | None = None) -> list[dict[str, Any]] | dict[str, Any]:
    """Return runtime metadata with current availability."""
    if runtime is not None:
        spec = get_runtime_spec(runtime)
        return spec.as_dict(available=is_runtime_available(runtime))
    return [spec.as_dict(available=is_runtime_available(spec.name)) for spec in _RUNTIME_SPECS.values()]


def require_runtime(runtime: str) -> RuntimeSpec:
    """Return a runtime spec or raise install guidance if unavailable."""
    spec = get_runtime_spec(runtime)
    if not is_runtime_available(runtime):
        raise RuntimeUnavailableError(runtime, spec.install)
    return spec


def load_runner(runtime: str) -> Any:
    """Instantiate a runner from the lazy registry."""
    spec = require_runtime(runtime)
    module = importlib.import_module(spec.runner_module)
    runner_cls = getattr(module, spec.runner_class)
    return runner_cls()


def install_command(runtime: str) -> str:
    """Return the install command for one registered runtime."""
    return get_runtime_spec(runtime).install


register_runtime(
    RuntimeSpec(
        name="crewai",
        import_name="crewai",
        runner_module="agentic_fabric.runners.crewai_runner",
        runner_class="CrewAIRunner",
        install="pip install crewai",
        extra=None,
        description="CrewAI orchestration through an externally installed CrewAI runtime.",
    )
)
register_runtime(
    RuntimeSpec(
        name="langgraph",
        import_name="langgraph",
        runner_module="agentic_fabric.runners.langgraph_runner",
        runner_class="LangGraphRunner",
        install='pip install "agentic-fabric[langgraph]"',
        extra="langgraph",
        description="LangGraph ReAct and graph workflows.",
    )
)
register_runtime(
    RuntimeSpec(
        name="strands",
        import_name="strands",
        runner_module="agentic_fabric.runners.strands_runner",
        runner_class="StrandsRunner",
        install='pip install "agentic-fabric[strands]"',
        extra="strands",
        description="AWS Strands single-agent workflow execution.",
    )
)
