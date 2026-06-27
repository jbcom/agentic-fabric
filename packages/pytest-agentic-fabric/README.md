# pytest-agentic-fabric

Pytest fixtures for projects built on `agentic-fabric`.

Fixtures:

- `agentic_runtime_available`: importability predicate for optional runtimes.
- `agentic_runtime_registry`: isolated mutable registry for tests.
- `agentic_runtime_modules`: known runtime import module names.
- `agentic_mock_runtime`: installs fake runtime modules into `sys.modules`.
- `agentic_fabric_agent_config`: minimal framework-neutral fabric agent config.
- `agentic_workspace`: temporary workspace with a discoverable `.fabric` package.

Tests marked `@pytest.mark.agentic_e2e` or
`@pytest.mark.agentic_runtime("crewai")` are skipped unless
`--agentic-e2e` is passed.
