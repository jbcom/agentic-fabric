"""Inspect MCP adapter entry points without importing optional providers."""

from __future__ import annotations

import json

from typing import Any

from agentic_fabric.tools import meshy_mcp, vendor_mcp


def inspect_mcp_adapters() -> dict[str, Any]:
    """Return deterministic MCP adapter configuration examples."""
    return {
        "extra": "mcp",
        "entry_points": {
            "vendor": "agentic-fabric-vendor-mcp",
            "meshy": "agentic-fabric-meshy-mcp",
        },
        "install_guidance": {
            "mcp": vendor_mcp.MCP_INSTALL_MESSAGE,
            "vendor": vendor_mcp.VENDOR_INSTALL_MESSAGE,
            "meshy": meshy_mcp.VENDOR_INSTALL_MESSAGE,
        },
        "client_config": {
            "mcpServers": {
                "vendor-fabric": {
                    "command": "agentic-fabric-vendor-mcp",
                },
                "meshy": {
                    "command": "agentic-fabric-meshy-mcp",
                    "env": {"MESHY_API_KEY": "<set-in-shell-or-client-secret-store>"},
                },
            }
        },
    }


def main() -> None:
    """Print MCP adapter metadata as JSON."""
    print(json.dumps(inspect_mcp_adapters(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
