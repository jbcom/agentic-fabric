"""Vendor-backed agent tool wrappers."""

from __future__ import annotations

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
    ) -> None:
        """Initialize a lazy wrapper for one provider operation."""
        self.provider = provider
        self.operation = operation
        self.name = f"{provider}_{operation}".replace("-", "_")
        self.description = description or f"Run vendor-fabric operation {operation!r} on provider {provider!r}."
        self.data = data

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
