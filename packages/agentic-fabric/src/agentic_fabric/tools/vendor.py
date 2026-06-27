"""Vendor-backed agent tool wrappers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class VendorCapabilityTool:
    """Generic tool that routes work through AgenticData/VendorData."""

    def __init__(
        self,
        provider: str,
        operation: str,
        *,
        data: Any | None = None,
        description: str | None = None,
        metadata: Any | None = None,
    ) -> None:
        """Initialize a lazy wrapper for one provider operation."""
        self.provider = provider
        self.operation = operation
        self.name = f"{provider}_{operation}".replace("-", "_")
        self.description = description or f"Run vendor-fabric operation {operation!r} on provider {provider!r}."
        self.data = data
        self.metadata = metadata

    @classmethod
    def from_metadata(cls, metadata: Any, *, data: Any | None = None) -> VendorCapabilityTool:
        """Build a tool wrapper from one ``VendorData.capabilities()`` item."""
        provider = str(_metadata_value(metadata, "provider", "")).strip()
        operation = str(_metadata_value(metadata, "operation", "")).strip()
        if not provider or not operation:
            msg = "Vendor capability metadata requires provider and operation"
            raise ValueError(msg)
        description = str(_metadata_value(metadata, "description", "")).strip() or None
        return cls(provider, operation, data=data, description=description, metadata=metadata)

    def _run(self, **kwargs: Any) -> Any:
        """Execute the vendor operation with keyword arguments."""
        data = self.data
        if data is None:
            from agentic_fabric.agentic_data import AgenticData

            data = AgenticData()
        return data.call(self.operation, self.provider, **kwargs)

    def __call__(self, **kwargs: Any) -> Any:
        """Allow framework adapters to treat this as a plain callable."""
        return self._run(**kwargs)


def vendor_capability_tools(
    data: Any | None = None,
    *,
    provider: str | None = None,
    include_unavailable: bool = True,
) -> list[VendorCapabilityTool]:
    """Return agent-facing tools for capabilities exposed by ``VendorData``."""
    if data is None:
        from agentic_fabric.agentic_data import AgenticData

        data = AgenticData()

    capabilities = getattr(data, "capabilities", None)
    if not callable(capabilities):
        return []

    raw_capabilities = (
        capabilities(provider, include_unavailable=include_unavailable)
        if provider is not None
        else capabilities(include_unavailable=include_unavailable)
    )

    tools: list[VendorCapabilityTool] = []
    for capability in raw_capabilities:
        try:
            tools.append(VendorCapabilityTool.from_metadata(capability, data=data))
        except ValueError:
            continue
    return tools


def _metadata_value(metadata: Any, key: str, default: Any) -> Any:
    """Read capability metadata from mappings or Extended Data-like objects."""
    if isinstance(metadata, Mapping):
        return metadata.get(key, default)

    getter = getattr(metadata, "get", None)
    if callable(getter):
        return getter(key, default)

    return getattr(metadata, key, default)
