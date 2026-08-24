# Agentic Fabric Workspace

![Woven configuration, runtime, and tool boundaries flowing through Agentic Fabric.](docs/assets/agentic-fabric-hero.jpg)

This repository is the public `jbcom/agentic-fabric` workspace.

Documentation: [jonbogaty.com/agentic-fabric](https://jonbogaty.com/agentic-fabric/)

Read `AGENTS.md` first in Codex sessions; it contains durable repository
guidance, validation commands, and package boundary rules.

The implemented surface includes `AgenticData`, lazy runtime registry metadata,
capability decorators, vendor-tool references, A2A 1.0 JSON-RPC applications,
MCP 2.0 tool servers, and the sibling `pytest-agentic-fabric` package.

`vendor-fabric` is the required provider layer. Agentic Fabric exposes its
public capability facade to agents; provider discovery, credentials, connector
implementation, and network calls stay in Vendor Fabric.

```bash
pip install "agentic-fabric[a2a,mcp,github]"
agentic-fabric-vendor-a2a --url https://agents.example.com/a2a
agentic-fabric-vendor-mcp
```

See the [package README](packages/agentic-fabric/README.md) for protocol
contracts, deployment guidance, and supported vendor extras.
