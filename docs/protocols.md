---
title: A2A and MCP interfaces
description: Protocol adapters for agent discovery, JSON-RPC tasks, and MCP tools.
---

The protocol layer belongs to `agentic-fabric`; provider implementation belongs to `vendor-fabric`. Both interfaces are adapters over public `AgenticData` and `VendorData` behavior, not alternate connector stacks.

## A2A 1.0

The `a2a` extra uses the official A2A Python SDK 1.x and implements the A2A 1.0 JSON-RPC binding. `create_a2a_app` serves public Agent Card discovery at `/.well-known/agent-card.json` and the JSON-RPC path declared by the first `AgentInterface`. Cards advertise streaming and explicitly do not advertise push notifications.

`A2AAgentSpec` is the stable application boundary. Its handler receives an `A2ARequest` containing normalized text, data parts, metadata, and task identifiers. The executor emits the Task first, a working update, one text or data artifact, and exactly one completed or failed terminal update. Cancellation emits a canceled terminal update.

Two factory paths are included:

- `create_fabric_agent_spec` sends a message and data parts to a registered or inline fabric agent through `AgenticData.run_fabric_agent`.
- `create_vendor_agent_spec` requires a JSON object with `provider`, `operation`, and optional `arguments` and calls `AgenticData.call(operation, provider, **arguments)`.

The bundled CLI is a local development server:

``` bash
agentic-fabric-vendor-a2a --host 127.0.0.1 --port 8000 \
  --url https://agents.example.com/a2a
```

The advertised URL is part of the interoperability contract and must be the client-reachable URL, not an internal bind address. Production applications should mount the returned Starlette routes inside their own authenticated ASGI stack and replace `InMemoryTaskStore` when task survival matters. REST, gRPC, push notifications, card signing, and a persistent task store are deliberately not claimed by this adapter.

## MCP 2026-07-28

The `mcp` extra requires the stable MCP Python SDK 2.x. The generic `MCPToolAdapter` describes a finite tool name, description, input schema, callable, and optional output schema. `create_tool_server` constructs the SDK's low-level server with explicit list and call handlers.

The server enforces these contracts:

- tool names are unique;
- every input schema and declared output schema is valid Draft 2020-12 JSON Schema;
- every invocation is validated before its callable runs;
- structured results conform to a declared output schema;
- successful and failed calls return typed `CallToolResult` values with structured content and a serialized text fallback;
- input or execution failures set `isError`; unknown tools raise an MCP invalid-parameters protocol error.

`agentic-fabric-vendor-mcp` enumerates only capabilities that `VendorData.capabilities(include_unavailable=False)` reports as available. It obtains method signatures from the public `get_connector_class` API to describe inputs, then invokes the route through `AgenticData.call`. Catalog tools use public package functions. `agentic-fabric-meshy-mcp` consumes the provider-owned Meshy tool definitions without moving their functions or models into this package.

Both shipped MCP commands use stdio. Callers that need Streamable HTTP should mount the returned SDK server in an application that owns authentication, authorization, rate limits, transport configuration, and audit policy.

## Specifications

- [A2A Protocol 1.0 specification](https://a2a-protocol.org/latest/specification/)
- [A2A Python SDK API](https://a2a-protocol.org/latest/sdk/python/api/)
- [MCP 2026-07-28 tools specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)
- [MCP Python SDK v2 migration guide](https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md)
