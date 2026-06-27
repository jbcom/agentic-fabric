"""Capability metadata for agent runners and tools."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, ClassVar, TypeVar, cast


F = TypeVar("F", bound=Callable[..., Any])


@dataclass(frozen=True)
class AgentCapabilitySpec:
    """A declared agent/runtime/tool capability."""

    name: str
    kind: str = "runtime"
    aliases: tuple[str, ...] = ()
    description: str = ""

    def as_dict(self) -> dict[str, Any]:
        """Return serializable capability metadata."""
        return {
            "name": self.name,
            "kind": self.kind,
            "aliases": list(self.aliases),
            "description": self.description,
        }


def agent_capability(
    name: str,
    *,
    kind: str = "runtime",
    aliases: tuple[str, ...] = (),
    description: str = "",
) -> Callable[[F], F]:
    """Declare an agent-facing capability on a method."""

    def decorate(method: F) -> F:
        specs = list(getattr(method, "_agentic_capabilities", ()))
        specs.append(
            AgentCapabilitySpec(
                name=name,
                kind=kind,
                aliases=aliases,
                description=description,
            )
        )
        cast("Any", method)._agentic_capabilities = tuple(specs)
        return method

    return decorate


def runtime_capability(
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    description: str = "",
) -> Callable[[F], F]:
    """Declare a runner/runtime capability."""
    return agent_capability(name, kind="runtime", aliases=aliases, description=description)


def tool_capability(
    name: str,
    *,
    aliases: tuple[str, ...] = (),
    description: str = "",
) -> Callable[[F], F]:
    """Declare a tool capability."""
    return agent_capability(name, kind="tool", aliases=aliases, description=description)


class AgentCapabilityProviderMixin:
    """Collect decorated capability declarations through inheritance."""

    agent_capabilities: ClassVar[Mapping[str, AgentCapabilitySpec]]
    agent_capability_methods: ClassVar[Mapping[str, str]]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        """Collect decorated methods across the full MRO."""
        super().__init_subclass__(**kwargs)
        capabilities: dict[str, AgentCapabilitySpec] = {}
        methods: dict[str, str] = {}

        for owner in reversed(cls.__mro__):
            for method_name, member in getattr(owner, "__dict__", {}).items():
                specs = cast("tuple[AgentCapabilitySpec, ...]", getattr(member, "_agentic_capabilities", ()))
                for spec in specs:
                    for public_name in (spec.name, *spec.aliases):
                        capabilities[public_name] = spec
                        methods[public_name] = method_name

        cls.agent_capabilities = MappingProxyType(capabilities)
        cls.agent_capability_methods = MappingProxyType(methods)

    @classmethod
    def list_capabilities(cls, *, kind: str | None = None) -> tuple[AgentCapabilitySpec, ...]:
        """Return declared capabilities, optionally filtered by kind."""
        capabilities = list(cls.agent_capabilities.values())
        if kind is not None:
            capabilities = [capability for capability in capabilities if capability.kind == kind]
        return tuple(capabilities)

    def call_capability(self, name: str, *args: Any, **kwargs: Any) -> Any:
        """Dispatch one declared capability by public name."""
        method_name = self.agent_capability_methods.get(name)
        if method_name is None:
            msg = f"Unknown agent capability: {name}"
            raise AttributeError(msg)
        method = getattr(self, method_name)
        if not callable(method):
            msg = f"Agent capability {name!r} is not callable"
            raise TypeError(msg)
        return method(*args, **kwargs)

    def capability_map(self) -> Mapping[str, AgentCapabilitySpec]:
        """Return read-only capability metadata for this instance."""
        return self.agent_capabilities
