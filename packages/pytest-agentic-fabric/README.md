# pytest-agentic-fabric

Pytest fixtures for projects built on `agentic-fabric`.

Fixtures:

- `agentic_runtime_available`: importability predicate for optional runtimes.
- `agentic_runtime_registry`: isolated mutable registry for tests.
- `agentic_runtime_modules`: known runtime import module names.
- `agentic_mock_runtime`: installs fake runtime modules into `sys.modules`.
- `agentic_fabric_agent_config`: minimal framework-neutral fabric agent config.
- `agentic_workspace`: temporary workspace with a discoverable `.fabric` package.

`agentic_workspace` serializes the current `agentic_fabric_agent_config`
fixture into `packages/sample/.fabric/manifest.yaml` plus matching
`agents.yaml` and `tasks.yaml` files. Override `agentic_fabric_agent_config`
in a test module or `conftest.py` to create a custom workspace while keeping
the discovery layout consistent.

Tests marked `@pytest.mark.agentic_e2e` or
`@pytest.mark.agentic_runtime("crewai")` are skipped unless
`--agentic-e2e` is passed.
