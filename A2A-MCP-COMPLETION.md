# A2A and MCP Completion Record

Date: 2026-08-12

Branch: `codex/a2a-mcp-interfaces`

Starting commit: `e31b7ff`

## State Found

The starting point was not “no protocol work.” Its two surfaces were at very
different stages:

- A2A had no source module, dependency, console entry point, tests, example, or
  documentation. It was absent, not stubbed.
- MCP was already substantial: `vendor_mcp.py` and `meshy_mcp.py`, two stdio
  console entry points, an executable example, README/Sphinx documentation, and
  a large adapter test suite existed.
- The MCP implementation targeted the 1.x Python SDK decorator API and returned
  text-only content lists. The unconstrained `mcp>=1.0.0` extra would now select
  the incompatible 2.x stable line on a fresh install.
- The generic vendor MCP server discovered connector classes through the private
  `vendor_fabric.registry._list_connector_classes` implementation detail.
- `AgenticData` had an import-time fallback superclass. That kept the agent
  package importable without Vendor Fabric but also made the intended
  `ExtendedData -> VendorData -> AgenticData` contract conditional.
- Documentation explicitly deferred Vendor Fabric passthrough extras.

The sibling Vendor Fabric checkout identifies itself as 2.1.5 and declares
stable extras for `anthropic`, `aws`, `cursor`, `github`, `google`, `meshy`,
`secrets-sync`, `slack`, `vault`, and `zoom`. Its public root exposes catalog
functions and `get_connector_class`; `VendorData` exposes `capabilities()` and
`call()`. Those are sufficient for this package, so no connector implementation
was copied.

## Current Specifications Used

- A2A Protocol 1.0 specification:
  <https://a2a-protocol.org/latest/specification/>
- Official A2A Python SDK and current API:
  <https://github.com/a2aproject/a2a-python> and
  <https://a2a-protocol.org/latest/sdk/python/api/>
- A2A Python SDK 1.1.2 package metadata:
  <https://pypi.org/project/a2a-sdk/>
- MCP 2026-07-28 tools specification:
  <https://modelcontextprotocol.io/specification/2026-07-28/server/tools>
- MCP Python SDK v2 migration and current behavior:
  <https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/migration.md>
  and <https://github.com/modelcontextprotocol/python-sdk/blob/main/docs/whats-new.md>
- MCP Python SDK 2.0.0 package metadata:
  <https://pypi.org/project/mcp/>

The important moving targets were A2A's 1.0 Agent Interface/card and PascalCase
JSON-RPC binding, and MCP's stable 2.0 SDK plus 2026-07-28 protocol. MCP 2.x no
longer uses the low-level 1.x decorators; tool handlers receive request context
and typed parameters and return full typed results. Structured content may be
any JSON value, should include a text fallback, and must match a declared output
schema. Servers must validate tool inputs.

## Built

### Dependency and layer contract

- `vendor-fabric>=2.1.5,<3` is a required package dependency.
- Matching provider passthrough extras are declared without importing provider
  SDKs eagerly.
- `AgenticData` now directly subclasses `VendorData`; the local provider
  fallback was removed.
- A2A and MCP SDK imports remain lazy behind the `a2a` and `mcp` extras.

### A2A 1.0

- Added public `A2ASkillSpec`, `A2ARequest`, and `A2AAgentSpec` boundaries.
- Added Agent Card construction with an explicit JSON-RPC 1.0
  `AgentInterface`, discovery routes, JSON-RPC routes, and a Starlette app
  factory using the official SDK.
- Added a task executor that emits the Task first, working status, one text or
  data artifact, and a completed/failed/canceled terminal lifecycle.
- Added a fabric-agent adapter through `AgenticData.run_fabric_agent()`.
- Added a structured vendor adapter accepting `provider`, `operation`, and
  `arguments`, dispatching only through `AgenticData.call()`.
- Added `agentic-fabric-vendor-a2a` as a local Uvicorn entry point.
- Result artifacts use Extended Data lowering and redaction; failure status
  text does not expose exception contents.

### MCP 2.x / 2026-07-28

- Added provider-neutral `MCPToolAdapter`, `create_tool_server()`, and
  `run_tool_server()` APIs.
- Migrated the servers from the MCP 1.x decorator API to 2.x constructor
  handlers and typed `ListToolsResult` / `CallToolResult` values.
- Enforced unique tool names and Draft 2020-12 schema validity.
- Validated every invocation before execution and validated structured results
  whenever an output schema is declared.
- Returned structured content plus serialized text fallback. Execution and
  validation failures set `isError`; unknown tool names are MCP protocol
  errors.
- Rebuilt the generic vendor server using public Vendor Fabric catalog APIs,
  `VendorData.capabilities(include_unavailable=False)`, public
  `get_connector_class`, and `AgenticData.call()` via `VendorCapabilityTool`.
  No private registry function or connector implementation is imported.
- Retained Meshy as a focused adapter over the provider-owned tool definitions.
- Verified the generic server in memory with the real cached MCP 2.0.0 SDK and
  client (`MCP_V2_SMOKE=PASS`).

### Documentation

- Updated both READMEs, durable boundary notes, examples, and Sphinx guides.
- Added `docs/protocols.rst` and generated API coverage for the A2A and generic
  MCP modules.
- Documented production authentication/rate-limit/durable-store obligations and
  the deliberately supported protocol/transport subsets.

## Test and Mutation Evidence

Restored source results:

- Agentic Fabric package: 503 passed, 17 existing opt-in E2E/framework skips.
- Coverage: 100% (`2547` statements, `0` missed).
- `pytest-agentic-fabric`: 27 passed.
- Ruff check and formatting: pass.
- Mypy: 40 source files, no issues.
- Sphinx/Furo with warnings fatal: pass.
- All four shipped examples: pass.
- A2A and `AgenticData` focused tests: 38 passed on Python 3.11, 3.12, 3.13,
  and 3.14.
- Both package sdists and wheels built with Hatchling; wheel metadata contains
  the required Vendor Fabric dependency and all A2A/MCP/provider extras.

Temporary mutations were made one at a time and fully restored:

1. Changed A2A successful terminal state from completed to failed. The lifecycle
   assertion failed (`failed != completed`).
2. Removed MCP output-schema validation. The invalid-output test failed because
   the call incorrectly returned `is_error=False`.
3. Removed the provider prefix from vendor MCP tool names. The public-capability
   call and stable-name assertions both failed.

The restored focused protocol/data suite is 56 passed. No mutation remains in
the worktree.

## Deliberately Left

- A2A advertises and implements JSON-RPC only. REST/HTTP+JSON and gRPC are not
  claimed.
- A2A push notifications, Agent Card signing, production authentication,
  authorization, rate limiting, and a persistent task store are application
  deployment concerns. The supplied CLI binds locally by default and uses an
  in-memory task store.
- Shipped MCP CLIs use stdio. The returned SDK server can be mounted by an
  application over another MCP 2.x transport, but this package does not invent
  that application's HTTP security policy.
- No live provider calls were made and no credentials were used. Provider
  behavior remains Vendor Fabric's responsibility.

## External Release/Lock Blocker

`uv.lock` is intentionally not hand-edited. As of this work, public PyPI returns
404 for `vendor-fabric`, so the new required dependency cannot be resolved from
the package's declared registry source. This execution environment also blocks
DNS, and its default `uv` cache is read-only; therefore it could not fetch the
new A2A 1.1.2 or MCP 2.0.0 resolution and regenerate the lock honestly.

Source, test, type, docs, example, real-MCP-smoke, coverage, and artifact-build
gates are green using the read-only sibling Vendor Fabric source and installed
dependency environments. A normal `uv sync --locked`, fresh tox environment
creation, and resolved `pip-audit` remain blocked until Vendor Fabric is
published or an approved durable package index/source is declared.

## Next Agent

1. Confirm the coordinated Vendor Fabric change is released at a resolvable
   source with version at least 2.1.5. If the release version changes, update
   only the dependency bounds; do not copy connector logic here.
2. Run `uv lock` with network access and commit the regenerated lock. Do not
   manufacture lock entries or point the published package at a developer-local
   sibling path.
3. Run the repository's full preferred gate chain, especially
   `uv sync --all-packages --all-extras --dev`, all four tox Python environments,
   `tox -e audit`, and `tox -e build` from the resolved lock.
4. Install the official A2A SDK from that lock and add an actual SDK/ASGI client
   smoke or A2A conformance/TCK run. Unit tests currently use a faithful fake of
   the documented 1.1.2 server API because that wheel was not present locally.

## Commits

- `d9deb71 feat: add A2A and MCP v2 vendor interfaces`
- `8b74068 docs: define A2A MCP and vendor boundaries`
- `5ba81f4 test: close protocol coverage gaps`

No push or pull request was performed.
