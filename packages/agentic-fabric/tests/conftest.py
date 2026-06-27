"""Pytest configuration for agentic-fabric tests."""

from __future__ import annotations

import os

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from pytest_agentic_fabric.mocking import (  # noqa: F401
    fabric_mocker,
    mock_agentic_frameworks,
    mock_crewai,
    mock_langgraph,
    mock_strands,
)
from pytest_agentic_fabric.plugin import (  # noqa: F401
    check_api_key,
    check_aws_credentials,
    fabric_agent_with_knowledge,
    multi_agent_fabric_agent_config,
    simple_agent_config,
    simple_fabric_agent_config,
    simple_task_config,
    temp_fabric_dir,
)


def pytest_addoption(parser: Any) -> None:
    """Register test-suite options for live E2E coverage."""
    parser.addoption(
        "--e2e",
        action="store_true",
        default=False,
        help="Run E2E tests that require real framework runtimes and external credentials",
    )
    parser.addoption(
        "--framework",
        action="store",
        choices=("crewai", "langgraph", "strands"),
        default=None,
        help="Run E2E tests for a single framework",
    )


def pytest_collection_modifyitems(config: Any, items: list[pytest.Item]) -> None:
    """Skip live E2E tests unless explicitly enabled and filter by framework."""
    e2e_enabled = config.getoption("--e2e")
    framework_filter = config.getoption("--framework")

    skip_e2e = pytest.mark.skip(reason="E2E tests disabled; pass --e2e to run them")
    skip_framework = pytest.mark.skip(reason=f"Test not selected by --framework={framework_filter}")
    framework_markers = {"crewai", "langgraph", "strands"}

    for item in items:
        if "e2e" in item.keywords and not e2e_enabled:
            item.add_marker(skip_e2e)

        if framework_filter:
            test_frameworks = framework_markers.intersection(item.keywords)
            if test_frameworks and framework_filter not in test_frameworks:
                item.add_marker(skip_framework)


@pytest.fixture(autouse=True)
def mock_llm_env(request: pytest.FixtureRequest) -> Generator[None, Any, None]:
    """Set up test environment with mocked LLM credentials."""
    if "e2e" in request.node.keywords:
        yield
        return

    # Set dummy API keys for testing (will be mocked anyway)
    with patch.dict(
        os.environ,
        {
            "OPENAI_API_KEY": "sk-test-mock-key",
            "ANTHROPIC_API_KEY": "sk-ant-test-mock-key",
            "CREWAI_TESTING": "true",
        },
    ):
        yield


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace with package structure."""
    # Create packages directory structure
    packages_dir = tmp_path / "packages"
    packages_dir.mkdir()

    # Create a mock sample package with framework-agnostic .fabric structure
    sample_dir = packages_dir / "sample"
    sample_dir.mkdir()

    fabric_dir = sample_dir / ".fabric"
    fabric_dir.mkdir()

    # Create minimal manifest (dict format, not list)
    manifest = fabric_dir / "manifest.yaml"
    manifest.write_text(
        """
name: sample
description: Test package
fabric_agents:
  test_fabric_agent:
    description: A test fabric agent
    agents: fabric_agents/test_fabric_agent/agents.yaml
    tasks: fabric_agents/test_fabric_agent/tasks.yaml
""",
        encoding="utf-8",
    )

    # Create fabric_agents directory
    fabric_agents_dir = fabric_dir / "fabric_agents" / "test_fabric_agent"
    fabric_agents_dir.mkdir(parents=True)

    # Create minimal agent and task configs
    (fabric_agents_dir / "agents.yaml").write_text(
        """
test_agent:
  role: Test Agent
  goal: Test goal
  backstory: Test backstory
""",
        encoding="utf-8",
    )

    (fabric_agents_dir / "tasks.yaml").write_text(
        """
test_task:
  description: Test task description
  expected_output: Test output
  agent: test_agent
""",
        encoding="utf-8",
    )

    return tmp_path


@pytest.fixture
def mock_fabric_agent_result() -> MagicMock:
    """Create a mock fabric agent result."""
    result = MagicMock()
    result.raw = {"output": "test output", "success": True}
    return result
