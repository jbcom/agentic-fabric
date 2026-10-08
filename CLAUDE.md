# Contributor guidance

This Python workspace contains `agentic-fabric`, a framework-agnostic agent
orchestration library, and `pytest-agentic-fabric`, its pytest fixtures and mocks.
Read `AGENTS.md` for package boundaries and implementation conventions.

## Development

Install dependencies with `uv sync --all-packages --all-extras --dev`.
Commands are defined in `tox.ini`; use `uvx --with tox-uv tox -e <env>`
when tox is not installed locally.

- Run `tox -e lint` for Ruff checks and formatting validation.
- Run `tox -e typecheck` for mypy checks.
- Run `tox -e py311,py312,py313,py314` for the supported Python versions.
  Missing interpreters must not be skipped.
- Run `tox -e coverage` for full coverage of both publishable packages.
- Run `tox -e plugin,examples,audit` for fixtures, examples, and dependency checks.
- Run `tox -e docs` for generated API validation and Sourcey documentation checks.
- Run `tox -e build` to build source and wheel distributions for both packages.
- Run `pre-commit run --all-files` before committing.

## Conventions

Keep optional framework imports lazy and registry-backed. Route provider tools
through `vendor-fabric` capabilities. Use logging, warnings, or exceptions in
library runtime code; CLI commands and examples may print user-facing output.
Keep implementation, tests, examples, README files, and Sourcey pages aligned.

Documentation lives in Markdown under `docs/`, with configuration in
`docs/sourcey.config.ts`. After changing public exports, regenerate the API
reference with `python scripts/generate_api_reference.py`. Do not commit
generated `docs/dist/` output.

Use topic branches, Conventional Commits, and merge commits. Release-please
manages package versions and tags; do not edit them manually.
