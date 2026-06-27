# Repository Instructions

This repository contains the `agentic-fabric` Python workspace.

## Active Goal

Finish this repository after `extended-data` and `vendor-fabric`. Its immediate
purpose is to hold all agent runtime architecture and make the remaining
migration unambiguous.

The active work branch is:

```bash
codex/agentic-fabric-bootstrap
```

Use the canonical checkout only:

```bash
/Users/jbogaty/src/jbcom/agentic-fabric
```

Do not create or continue side worktrees for this repo.

## Related Repositories

`agentic-fabric` depends on both upstream layers. Periodically check their local
and remote state before finalizing this repo.

| Layer | Local checkout | Remote | Branch |
| --- | --- | --- | --- |
| Upstream base data | `/Users/jbogaty/src/jbcom/extended-data` | `https://github.com/jbcom/extended-data` | `codex/extended-data-polymorphic-container` |
| Upstream vendor layer | `/Users/jbogaty/src/jbcom/vendor-fabric` | `https://github.com/jbcom/vendor-fabric` | `codex/vendor-fabric-extended-data-boundary` |
| Current repo | `/Users/jbogaty/src/jbcom/agentic-fabric` | `https://github.com/jbcom/agentic-fabric` | `codex/agentic-fabric-bootstrap` |
| Legacy monorepo | `/Users/jbogaty/src/jbcom/extended-data-library` | `https://github.com/jbcom/extended-data-library` | `main` |
| Legacy agent repo | `/Users/jbogaty/src/jbcom/agentic` | `https://github.com/jbcom/agentic` | check locally |

## Scope

`agentic-fabric` owns:

- framework-agnostic fabric agent discovery and loading
- runner adapters for CrewAI, LangGraph, Strands, and local CLI tools
- agent-facing tool resolution and framework adapter utilities
- planned optional passthrough dependencies to `vendor-fabric` after
  `vendor-fabric` is published
- `AgenticData` as the agent/runtime-aware extension of `VendorData`
- `pytest-agentic-fabric` for runner, tool, and framework fixture support
- Sphinx/Furo/autodoc2 docs for this workspace

`extended-data` owns base data primitives, logging, inputs, files, redaction,
and generic workflows. `vendor-fabric` owns vendor connectors, provider-backed
sync, the SecretSync Python facade and `VendorData` capability surface, and
provider dispatch. `agentic-fabric` owns agent-facing wrappers over those
capabilities.

## Architecture Docs

Read these before changing code:

- `docs/architecture.rst`: `AgenticData` and agent capability design
- `docs/pillars.rst`: package ownership principles
- `docs/vendor-fabric.rst`: dependency boundary with provider tooling

Legacy parity sources for this repo are:

- `/Users/jbogaty/src/jbcom/agentic`
- `/Users/jbogaty/src/jbcom/extended-data-library/packages/vendor-connectors/src/vendor_connectors/agentic`
- `/Users/jbogaty/src/jbcom/vendor-fabric/packages/vendor-fabric/src/vendor_fabric/agentic`
- `/Users/jbogaty/src/jbcom/vendor-fabric/packages/vendor-fabric/tests/agentic`
- `/Users/jbogaty/src/jbcom/vendor-fabric/packages/pytest-vendor-fabric/src/pytest_vendor_fabric/agentic`

Move agent runtime code here. Leave provider connector code in `vendor-fabric`.
Do not add `vendor-fabric` passthrough extras until `vendor-fabric` exists on
PyPI. The package currently has no resolvable PyPI release under that name.

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

## Release Flow

Releases are managed by release-please:

- `ci.yml` validates pull requests.
- `release.yml` opens and maintains the release-please PR.
- `cd.yml` publishes packages to PyPI and deploys Sphinx/Furo docs to GitHub
  Pages after releases are created.

Do not hand-edit versions or tags outside release-please work.

## Finish Criteria

This repo is not done until:

1. all agent runtime code from the legacy parity sources is represented here
2. provider connector code remains in `vendor-fabric`
3. `AgenticData` extends the vendor layer and routes agent/runtime capabilities
4. optional framework extras are lazy, discoverable, and documented
5. `pytest-agentic-fabric` is usable and separately publishable
6. docs, examples, tests, and README agree on the public API
7. Python 3.11 through 3.14 pass without skipped missing interpreters
8. a ready pull request is opened and reviewed
9. release-please and CD can publish packages and deploy docs

## Active Finish Plan

Use this section as the source of truth for finishing this WIP branch.

### Current Branch

```bash
git switch codex/agentic-fabric-bootstrap
```

Work only in `/Users/jbogaty/src/jbcom/agentic-fabric`.

Finish `extended-data` first. Then finish `vendor-fabric`. This package depends
on the final `ExtendedData` and `VendorData` contracts.

Before final validation, check local and remote state for both upstream repos.

### Code

- Keep runtime code under `packages/agentic-fabric`.
- Keep pytest helper code under `packages/pytest-agentic-fabric`.
- Implement `AgenticData` as a `VendorData` subclass with runtime context.
- Implement runner and tool capabilities through decorators collected by
  `__init_subclass__`.
- Keep optional framework imports lazy and registry-backed.
- Route vendor-backed tools through `vendor-fabric`; do not call SDKs directly
  from agent code.
- Add passthrough `vendor-fabric` extras only after `vendor-fabric` exists on
  PyPI. As of this handoff, `vendor-fabric` has no resolvable PyPI release under
  that name, so declaring passthrough extras makes `uv lock` fail.
- Use configured logging or Python logging/warnings/exceptions in library
  runtime paths. CLI commands and examples may write user-facing output.

### Docs

- Keep README, Sphinx guides, examples, and API docs aligned.
- Keep public docs in reStructuredText under `docs/`; do not add authored
  Markdown pages there.
- Keep architecture and pillar docs current when architecture changes.
- Document every supported runtime extra and unavailable-runtime behavior.
- Document framework priority and explicit runtime selection.

### Tests

- Cover runner registry behavior and capability dispatch.
- Cover optional framework dependencies as unavailable features with install
  guidance.
- Cover `AgenticData` active-runtime routing and explicit-runtime routing.
- Keep `pytest-agentic-fabric` tested as its own package.
- Run Python 3.11 through 3.14. Do not skip missing interpreters.

### GitHub

- Create the public `jbcom/agentic-fabric` repo if it does not exist.
- Push the active branch.
- Open a ready pull request, not a draft.
- Handle CI failures.
- Inspect and resolve actionable review feedback.
- Squash merge only after the PR is approved and green.
- Confirm release-please and CD can publish packages and deploy docs.

### Post-Finish AGENTS Cleanup

After this finish plan is complete and the PR is merged, compress this file to
durable repository guidance only. Remove branch-specific WIP instructions,
legacy migration checklist items, and temporary hand-off details. Keep the
canonical package scope, normal validation commands, release flow notes, and
stable downstream/upstream boundaries.
