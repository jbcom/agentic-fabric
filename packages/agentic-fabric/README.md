# agentic-fabric

[![PyPI version](https://img.shields.io/pypi/v/agentic-fabric.svg)](https://pypi.org/project/agentic-fabric/)
[![CI](https://github.com/jbcom/agentic-fabric/actions/workflows/ci.yml/badge.svg)](https://github.com/jbcom/agentic-fabric/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/pypi/pyversions/agentic-fabric.svg)](https://pypi.org/project/agentic-fabric/)

Framework-agnostic agent crew orchestration. Declare crews once in YAML, then
run them on CrewAI, LangGraph, Strands, or local CLI runners without changing a
single crew definition. Runtime frameworks are optional and are detected lazily
from what is installed.

[Documentation](https://jonbogaty.com/agentic-fabric/) | [Source](https://github.com/jbcom/agentic-fabric) | [Issues](https://github.com/jbcom/agentic-fabric/issues)

## Installation

```bash
# Core discovery, loading, and runner selection
pip install agentic-fabric

# With a specific framework
pip install "agentic-fabric[crewai]"
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
you use. The `crewai` and `scraping` extras include dependencies selected by
CrewAI. If a transitive CrewAI dependency has an upstream advisory with no
patched release, upgrading `agentic-fabric` alone cannot clear that advisory;
core/local-CLI installs are unaffected.

## Quick Start

### 1. Define a Crew (YAML)

```yaml
# .crewai/crews/analyzer/agents.yaml
code_reviewer:
  role: Senior Code Reviewer
  goal: Find bugs and improvements
  backstory: Expert at code analysis
```

```yaml
# .crewai/crews/analyzer/tasks.yaml
review_code:
  description: Review the provided code for issues
  expected_output: List of findings with severity
  agent: code_reviewer
```

### 2. Run It

```python
from pathlib import Path

from agentic_fabric import detect_framework, get_crew_config, run_crew_auto

# See what framework is available
framework = detect_framework()

# Load a crew manifest discovered in a package or workspace
config = get_crew_config(Path(".crew"), "analyzer")

# Auto-detect best framework and run
result = run_crew_auto(config, inputs={"code": "..."})
```

Or from the CLI:

```bash
agentic-fabric run my-package analyzer --input "Review this code: ..."
```

### 3. Use a Specific Runner

```python
from agentic_fabric import get_runner

runner = get_runner("langgraph")  # Force LangGraph
crew = runner.build_crew(config)
result = runner.run(crew, inputs)
```

### 4. Carry Runtime Context with Data

```python
from agentic_fabric import AgenticData, get_framework_info

print(get_framework_info())

session = AgenticData({"repo": "jbcom/agentic-fabric"})
session.register_agent("reviewer", config)
result = session.run_agent("reviewer", runtime="crewai")
```

## Key Features

- Framework agnostic: one crew definition, multiple runtime backends.
- Lazy imports: core package import does not require CrewAI, LangGraph,
  Strands, or vendor SDKs.
- Focused extras: `crewai`, `langgraph`, `strands`, `mcp`, `scraping`,
  `tests`, `typing`, `docs`, and `dev`.
- `AgenticData`: carries data, registered crews, active runtime selection, and
  vendor-layer context together.
- Capability decorators: runners and tools expose declared capabilities through
  read-only metadata and deterministic dispatch.
- Tool resolution: built-in, vendor URI, and registered factories are preferred;
  external dynamic imports require `AGENTIC_FABRIC_TOOL_IMPORT_ALLOWLIST`.
- YAML-first: crew configuration in YAML, not Python boilerplate.
- Hierarchical orchestration: `ManagerAgent` delegates across crews.
- Package discovery: finds `.crew/`, `.crewai/`, `.langgraph/`, and
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
their runtime: a crew in `.langgraph/` will not silently run on CrewAI.

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

## Repository Boundary

- `extended-data` owns base data containers, logging, input handling, files,
  redaction, and generic workflows.
- `vendor-fabric` owns vendor connectors, provider-backed sync, SecretSync for
  Python, and vendor-backed tool adapters.
- `agentic-fabric` owns crew discovery, runner selection, framework adapters, and
  orchestration.

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
tox -e lint
tox -e typecheck
tox -e py311
tox -e py312
tox -e py313
tox -e py314
tox -e build
```

## License

MIT
