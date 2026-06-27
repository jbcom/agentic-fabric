# pytest-agentic-fabric

Pytest fixtures for projects built on `agentic-fabric`.

Fixtures:

- `agentic_runtime_available`: importability predicate for optional runtimes.
- `agentic_runtime_registry`: isolated mutable registry for tests.
- `agentic_runtime_modules`: known runtime import module names.
- `agentic_mock_runtime`: installs fake runtime modules into `sys.modules`.
- `agentic_fabric_mocker` / `fabric_mocker`: `FabricMocker` helper for
  mocking CrewAI, LangGraph, Strands, and agentic-fabric internals.
- `mock_agentic_frameworks`: installs fake modules for all optional runtimes.
- `mock_crewai`, `mock_langgraph`, `mock_strands`: installs fake modules for
  one optional runtime path.
- `agentic_fabric_agent_config`: minimal framework-neutral fabric agent config.
- `simple_agent_config`, `simple_task_config`: reusable agent and task config
  mappings.
- `simple_fabric_agent_config`, `multi_agent_fabric_agent_config`,
  `fabric_agent_with_knowledge`: reusable fabric agent config mappings.
- `temp_fabric_dir`: temporary framework-agnostic `.fabric` directory.
- `agentic_workspace`: temporary workspace with a discoverable `.fabric` package.

`agentic_workspace` serializes the current `agentic_fabric_agent_config`
fixture into `packages/sample/.fabric/manifest.yaml` plus matching
`agents.yaml` and `tasks.yaml` files. Override `agentic_fabric_agent_config`
in a test module or `conftest.py` to create a custom workspace while keeping
the discovery layout consistent.

Tests marked `@pytest.mark.agentic_e2e` or
`@pytest.mark.agentic_runtime("crewai")` are skipped unless
`--agentic-e2e` is passed.

`FabricMocker` exposes `mock_crewai()`, `mock_langgraph()`, `mock_strands()`,
`mock_all_frameworks()`, framework-specific patch helpers, and
`patch_get_llm()`, `patch_discover_packages()`,
`patch_get_fabric_agent_config()`, and `patch_run_fabric_agent_auto()` for
tests that need to isolate fabric orchestration from optional runtime imports.
