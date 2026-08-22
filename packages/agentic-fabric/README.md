# agentic-fabric

[![PyPI version](https://img.shields.io/pypi/v/agentic-fabric.svg)](https://pypi.org/project/agentic-fabric/)
[![CI](https://github.com/jbcom/agentic-fabric/actions/workflows/ci.yml/badge.svg)](https://github.com/jbcom/agentic-fabric/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/pypi/pyversions/agentic-fabric.svg)](https://pypi.org/project/agentic-fabric/)

Framework-agnostic agent fabric orchestration. Declare fabric agents once in YAML, then
run them on CrewAI, LangGraph, Strands, or local CLI runners without changing a
single fabric agent definition. Runtime frameworks are optional and are detected lazily
from what is installed.

[Documentation](https://jonbogaty.com/agentic-fabric/) | [Source](https://github.com/jbcom/agentic-fabric) | [Issues](https://github.com/jbcom/agentic-fabric/issues)

## Installation

```bash
# Core discovery, loading, runner selection, local CLI, and neutral file tools
pip install agentic-fabric

# With a specific framework
pip install "agentic-fabric[langgraph]"
pip install "agentic-fabric[strands]"

# Non-framework optional surfaces
pip install "agentic-fabric[a2a]"
pip install "agentic-fabric[mcp]"
pip install "agentic-fabric[scraping]"

# Add only the provider SDKs the agent actually calls
pip install "agentic-fabric[github,slack]"
```

Local CLI runners do not require a Python extra. Install the external CLI
(`aider`, `claude`, `codex`, `ollama`, or a custom executable) and inspect
profiles with `agentic-fabric list-runners --json`.

`vendor-fabric` is a required dependency and owns provider routing. The
`anthropic`, `aws`, `cursor`, `github`, `google`, `meshy`, `secrets-sync`,
`slack`, `vault`, and `zoom` extras pass through to its matching optional
dependencies. Provider SDK imports remain lazy.

There is no aggregate AI extra. Install exactly the framework or provider path
you use. The CrewAI adapter remains lazy, but `agentic-fabric` does not publish
a CrewAI extra while CrewAI depends on ChromaDB releases covered by an upstream
critical advisory with no patched version. Install CrewAI separately only after
reviewing that advisory state. Core, local-CLI, and first-party scraping
installs are unaffected.

## Quick Start

### 1. Define a Fabric Agent (YAML)

```yaml
# .fabric/fabric_agents/analyzer/agents.yaml
code_reviewer:
  role: Senior Code Reviewer
  goal: Find bugs and improvements
  backstory: Expert at code analysis
```

```yaml
# .fabric/fabric_agents/analyzer/tasks.yaml
review_code:
  description: Review the provided code for issues
  expected_output: List of findings with severity
  agent: code_reviewer
```

### 2. Run It

```python
from pathlib import Path

from agentic_fabric import detect_framework, get_fabric_agent_config, run_fabric_agent_auto

# See what framework is available
framework = detect_framework()

# Load a fabric agent manifest discovered in a package or workspace
config = get_fabric_agent_config(Path(".fabric"), "analyzer")

# Auto-detect best framework and run
result = run_fabric_agent_auto(config, inputs={"code": "..."})
```

Or from the CLI:

```bash
agentic-fabric run my-package analyzer --input "Review this code: ..."
```

### 3. Use a Specific Runner

```python
from agentic_fabric import get_runner

runner = get_runner("langgraph")  # Force LangGraph
fabric_agent = runner.build_fabric_agent(config)
result = runner.run(fabric_agent, inputs)
```

### 4. Carry Runtime Context with Data

```python
from agentic_fabric import AgenticData, get_framework_info

print(get_framework_info())

session = AgenticData({"repo": "jbcom/agentic-fabric"})
session.register_fabric_agent("reviewer", config)
result = session.run_fabric_agent("reviewer", runtime="crewai")
```

## Key Features

- Framework agnostic: one fabric agent definition, multiple runtime backends.
- Lazy imports: core package import does not require CrewAI, LangGraph,
  Strands, or vendor SDKs.
- Framework-neutral file tools: built-in filesystem tools can be resolved
  without installing CrewAI or Pydantic; framework adapters add schema wrappers
  only when their optional dependencies are present.
- Focused extras: `langgraph`, `strands`, `a2a`, `mcp`, `scraping`,
  `tests`, `typing`, `docs`, and `dev`.
- `AgenticData`: carries data, registered fabric agents, active runtime selection, and
  vendor-layer context together.
- Capability decorators: runners and tools expose declared capabilities through
  read-only metadata and deterministic dispatch.
- Tool resolution: built-in, vendor URI, and registered factories are preferred;
  external dynamic imports require `AGENTIC_FABRIC_TOOL_IMPORT_ALLOWLIST`.
- Vendor tool catalogs: `AgenticData.vendor_tools()` adapts inherited
  `VendorData` capability metadata into agent-facing tools without importing
  provider SDKs directly.
- YAML-first: fabric agent configuration in YAML, not Python boilerplate.
- Hierarchical orchestration: `ManagerAgent` delegates across fabric agents.
- Package discovery: finds `.fabric/`, `.crewai/`, `.langgraph/`, and
  `.strands/` directories.
- Vendor passthrough extras install the matching `vendor-fabric` provider
  dependency without moving connector behavior into this package.
- CLI and library: use from the command line or import as a module.

## Framework Priority

1. CrewAI, if installed.
2. LangGraph, if CrewAI is unavailable.
3. Strands, if neither CrewAI nor LangGraph is available.

You can always force a specific runner with `get_runner("langgraph")` or
`agentic-fabric run --framework langgraph`.

If the selected runtime is not installed, errors point to the matching
`agentic-fabric[...]` extra. Framework-specific config directories also enforce
their runtime: a fabric agent in `.langgraph/` will not silently run on CrewAI.

## Local CLI Runners

For single-agent coding tools, use the `--runner` CLI path:

```bash
agentic-fabric list-runners --json
agentic-fabric run --runner aider --input "Add validation to auth.py"
agentic-fabric run --runner ollama --model deepseek-coder --input "Explain this module"
```

Profiles are loaded from the packaged `local_cli_profiles.yaml`, validated
before use, and rejected on POSIX systems if the profiles file is group- or
world-writable.

## A2A Interfaces

The `a2a` extra installs the official A2A Python SDK and Starlette/Uvicorn
HTTP surface. Agentic Fabric implements A2A Protocol 1.0 with Agent Card
discovery and the JSON-RPC binding:

```python
from agentic_fabric import create_fabric_agent_spec, create_a2a_app

spec = create_fabric_agent_spec("reviewer", "https://agents.example.com/a2a")
app = create_a2a_app(spec)
```

`create_vendor_a2a_app()` exposes a single structured skill accepting
`provider`, `operation`, and `arguments`; execution delegates to
`AgenticData.call()` and therefore to `VendorData`. The bundled development
entry point is:

```bash
agentic-fabric-vendor-a2a --host 127.0.0.1 --port 8000 \
  --url https://agents.example.com/a2a
```

The app uses an in-memory task store and declares streaming but not push
notifications. Wrap it with application authentication, authorization, rate
limits, audit logging, HTTPS, and a durable task store before production use.
Only JSON-RPC is advertised; HTTP+JSON/REST and gRPC are not silently claimed.

## MCP Adapters

The `mcp` extra installs the stable MCP Python SDK 2.x, which implements the
2026-07-28 protocol while retaining earlier-client compatibility. It enables
two stdio console entry points:

```bash
agentic-fabric-vendor-mcp
agentic-fabric-meshy-mcp
```

`agentic-fabric-vendor-mcp` exposes credential-free public catalog functions
and currently available `VendorData.capabilities()`. Calls route through
`AgenticData.call()`; the adapter never imports connector implementations or
uses Vendor Fabric's private registry. `agentic-fabric-meshy-mcp` converts
Meshy capability metadata from `vendor-fabric[meshy]` into MCP tools. Both
servers validate tool inputs against Draft 2020-12 JSON Schema and return both
structured content and a serialized text fallback. Declared output schemas are
also enforced. Provider results and diagnostics pass through Extended Data's
redaction helpers before leaving the process.

The generic `MCPToolAdapter` and `create_tool_server()` API can expose an
application-owned callable set without a vendor dependency. The shipped CLIs
use stdio; applications can mount the returned SDK server over another MCP 2.x
transport when they own the transport security policy.

## Repository Boundary

- `extended-data` owns base data containers, logging, input handling, files,
  redaction, and generic workflows.
- `vendor-fabric` owns vendor connectors, provider-backed sync, the SecretSync
  Python facade/capability surfaces, provider capability metadata, and provider
  dispatch.
- `agentic-fabric` owns fabric agent discovery, runner selection, framework
  adapters, A2A/MCP protocol surfaces, agent-facing tool wrappers, and
  orchestration.

Protocol behavior follows the current [A2A 1.0 specification](https://a2a-protocol.org/latest/specification/)
and [MCP 2026-07-28 tool specification](https://modelcontextprotocol.io/specification/2026-07-28/server/tools).

Full guides and API documentation are published at
[jonbogaty.com/agentic-fabric](https://jonbogaty.com/agentic-fabric/).
`AGENTS.md` contains durable repository guidance for Codex sessions.

## Documentation

The docs are built with Sphinx, Furo, and sphinx-autodoc2:

```bash
tox -e docs
```

Local validation:

```bash
uv sync --all-packages --all-extras --dev
tox -e lint
tox -e typecheck
tox -e audit
tox -e py311
tox -e py312
tox -e py313
tox -e py314
tox -e coverage
tox -e plugin
tox -e examples
tox -e build
```

## License

MIT
