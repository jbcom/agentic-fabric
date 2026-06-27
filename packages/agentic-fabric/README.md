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
pip install "agentic-fabric[mcp]"
pip install "agentic-fabric[scraping]"
```

Local CLI runners do not require a Python extra. Install the external CLI
(`aider`, `claude`, `codex`, `ollama`, or a custom executable) and inspect
profiles with `agentic-fabric list-runners --json`.

Vendor-backed passthrough extras will be added after the upstream
`vendor-fabric` optional-extra contract is published and stable. Until then,
vendor references stay lazy and report install guidance at use time.

There is no aggregate AI extra. Install exactly the framework or provider path
you use. The CrewAI adapter remains lazy, but `agentic-fabric` does not publish
a CrewAI extra while CrewAI depends on ChromaDB releases covered by an upstream
critical advisory with no patched version. Install CrewAI separately only after
reviewing that advisory state. Core, local-CLI, and first-party scraping
installs are unaffected.

## Quick Start

### 1. Define a Fabric Agent (YAML)

```yaml
# .crewai/fabric_agents/analyzer/agents.yaml
code_reviewer:
  role: Senior Code Reviewer
  goal: Find bugs and improvements
  backstory: Expert at code analysis
```

```yaml
# .crewai/fabric_agents/analyzer/tasks.yaml
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
- Focused extras: `langgraph`, `strands`, `mcp`, `scraping`,
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
- Vendor passthrough extras are deferred until `vendor-fabric` is published
  with a stable optional-extra contract.
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

## MCP Adapters

The `mcp` extra installs the MCP transport dependency and enables two console
entry points:

```bash
agentic-fabric-vendor-mcp
agentic-fabric-meshy-mcp
```

`agentic-fabric-vendor-mcp` exposes credential-free vendor catalog tools and
public `vendor-fabric` data methods. `agentic-fabric-meshy-mcp` converts
Meshy capability metadata from `vendor-fabric[meshy]` into MCP tools. Both
servers import provider code lazily; install the matching `vendor-fabric`
package/extras in the same environment before running provider-backed tools.
If provider startup fails, the adapter error includes the `agentic-fabric[mcp]`
or `vendor-fabric[...]` install guidance plus the original import failure so
missing provider extras are visible.

## Repository Boundary

- `extended-data` owns base data containers, logging, input handling, files,
  redaction, and generic workflows.
- `vendor-fabric` owns vendor connectors, provider-backed sync, the SecretSync
  Python facade/capability surfaces, provider capability metadata, and provider
  dispatch.
- `agentic-fabric` owns fabric agent discovery, runner selection, framework adapters,
  agent-facing tool wrappers, and orchestration.

Full guides and API documentation are published at
[jonbogaty.com/agentic-fabric](https://jonbogaty.com/agentic-fabric/).
`AGENTS.md` contains the active local migration plan for Codex sessions.

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
tox -e build
```

## License

MIT
