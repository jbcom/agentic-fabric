# Repository Instructions

This repository contains the `agentic-fabric` Python workspace.

## Scope

- `packages/agentic-fabric`: framework-agnostic agent discovery, runtime
  selection, runner adapters, agent-facing tool wrappers, and `AgenticData`
- `packages/pytest-agentic-fabric`: pytest fixtures and mocks for agentic
  runtime, tool, and framework tests
- `docs/`: Sphinx/Furo documentation and generated API reference

## Layer Boundaries

- `extended-data` owns base data containers, logging, input handling, files,
  redaction, and generic workflows.
- `vendor-fabric` owns vendor connectors, provider-backed sync, SecretSync
  Python facade/capability surfaces, provider capability metadata, and provider
  dispatch.
- `agentic-fabric` owns runtime discovery, runner selection, framework
  adapters, agent-facing tool wrappers, MCP surfaces, and orchestration.

`AgenticData` extends `VendorData`; it should not bypass the vendor layer or
recreate provider dispatch. Keep SecretSync access routed through
`vendor-fabric` capabilities rather than importing the Go binding directly.

## Preferred Commands

```bash
uv sync --all-packages --all-extras --dev
tox -e lint
tox -e typecheck
tox -e audit
tox -e py311,py312,py313,py314
tox -e coverage
tox -e plugin
tox -e examples
tox -e docs
tox -e build
```

Use `uvx --with tox-uv tox -e <env>` when tox is not installed locally.

Do not set `skip_missing_interpreters = true`. Python 3.11, 3.12, 3.13, and
3.14 are all part of the supported release contract.

## Expectations

- Keep README files, Sphinx docs, examples, tests, and implementation aligned.
- Keep optional framework imports lazy and registry-backed.
- Keep provider-backed tools routed through `vendor-fabric`; do not call vendor
  SDKs directly from agent runtime code.
- Use configured logging or Python logging/warnings/exceptions in library
  runtime paths. CLI commands and examples may write user-facing output.
- Prefer durable package guidance over branch-specific migration instructions.

## Release Flow

Releases are managed by release-please:

- `ci.yml` validates pull requests.
- `release.yml` opens and maintains the release-please PR.
- `cd.yml` publishes packages to PyPI and deploys Sphinx/Furo docs to GitHub
  Pages after releases are created.

Do not hand-edit versions or tags outside release-please work.
