<!-- profile: python-lib agent-state standard-repo v1 -->
# agentic-fabric

Framework-agnostic Python agent-fabric orchestration library: discovers YAML fabric-agent definitions, selects an installed runtime (CrewAI / LangGraph / Strands / local CLI), and runs the same fabric agent across runtimes. Workspace package; sibling `pytest-agentic-fabric` ships fixtures/mocks.

## Profiles loaded

@/Users/jbogaty/.claude/profiles/python-lib.md
@/Users/jbogaty/.claude/profiles/agent-state.md
@/Users/jbogaty/.claude/profiles/standard-repo.md

## Repo-specific

Commands are defined in `tox.ini` and run via `tox -e <env>` (use `uvx --with tox-uv tox -e <env>` if tox isn't installed). `skip_missing_interpreters = false` — Python 3.11/3.12/3.13/3.14 all must pass.

- **Sync:** `uv sync --all-packages --all-extras --dev`
- **Test:** `tox -e py311,py312,py313,py314` (all four Pythons are the release contract) · `tox -e plugin` for `pytest-agentic-fabric` tests · `tox -e examples` runs shipped example scripts
- **Lint:** `tox -e lint` (ruff check across src/tests/examples/docs/AGENTS.md/README.md)
- **Fmt:** `ruff format <paths>` (not a tox env; run via `uvx ruff format`)
- **Type-check:** `tox -e typecheck` (mypy, config in `packages/agentic-fabric/pyproject.toml`)
- **Coverage:** `tox -e coverage` — `--fail-under=100`, enforced per publishable package
- **Audit:** `tox -e audit` (pip-audit over all optional/test/typing extras)
- **Docs build:** `tox -e docs` (`sphinx-build -W -E -b html docs docs/_build/html`, Sphinx/Furo, autodoc2)
- **Build:** `tox -e build` (`uv build --package` for both packages → `dist/<pkg>/`)

## AGENTS.md

Extended operating protocols, package/layer boundaries, preferred commands, and release flow live in `AGENTS.md` — read it before non-trivial work. This CLAUDE.md deliberately does not restate that content (DRY). Topics `AGENTS.md` covers:

- Workspace scope: `packages/agentic-fabric` + `packages/pytest-agentic-fabric` + Sphinx `docs/`
- Layer boundaries: `extended-data` (data primitives) → `vendor-fabric` (vendor connectors, SecretSync facade, provider dispatch) → `agentic-fabric` (runtime discovery, runner adapters, agent tool wrappers, MCP). `AgenticData extends VendorData extends ExtendedData`; agent code must not call vendor SDKs directly.
- Preferred tox/uv commands and the "no `skip_missing_interpreters`, all four Pythons" rule.
- Expectations: README/docs/examples/tests stay aligned, optional framework imports stay lazy + registry-backed, vendor tools routed through `vendor-fabric` capabilities, library runtime uses logging (CLI/examples may write user-facing output).
- Release flow: release-please owns versions via `ci.yml` / `release.yml` / `cd.yml` (PyPI publish + GitHub Pages Sphinx deploy); do not hand-edit versions/tags.

## Notes

- **Pillars** (see `docs/pillars.rst`): Declare Once · Data And Context Move Together (`AgenticData` carries data + provider + runtime + logging + tool registry) · Lazy by Default · Capabilities Over Boilerplate (decorators + `__init_subclass__`, no custom dunders) · Clear Boundaries · Testable Adapters · Frameworks Are Optional, Contracts Are Not.
- **Architecture source of truth:** `docs/architecture.rst` — runtime selection precedence, capability registry (`agentic_fabric.capabilities`), `vendor://provider/operation` lazy tool references.
- Docs are Sphinx `.rst` under `docs/` (Furo theme); toctree in `docs/index.rst` covers getting-started, architecture, agentic-workflows, vendor-fabric, pillars, development, api/index. Docs build is treated as warnings-fatal (`-W -E`).
- Optional extras are install-gated: `[langgraph]`, `[strands]`, `[mcp]`, `[scraping]`; CrewAI stays lazy (upstream ChromaDB advisory). Vendor passthrough extras deferred until `vendor-fabric` publishes a stable extra contract.
- Coverage is 100% enforced per package — write tests in the same change as any public behavior.