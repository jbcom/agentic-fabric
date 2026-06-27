"""Pytest configuration for agentic-fabric tests."""

from __future__ import annotations

import os

from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tests._fabric_mocker import fabric_mocker, mock_crewai, mock_frameworks, mock_langgraph, mock_strands  # noqa: F401


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

    # Create a mock sample package with .crewai structure
    sample_dir = packages_dir / "sample"
    sample_dir.mkdir()

    crewai_dir = sample_dir / ".crewai"
    crewai_dir.mkdir()

    # Create minimal manifest (dict format, not list)
    manifest = crewai_dir / "manifest.yaml"
    manifest.write_text("""
name: sample
description: Test package
fabric_agents:
  test_fabric_agent:
    description: A test fabric agent
    agents: fabric_agents/test_fabric_agent/agents.yaml
    tasks: fabric_agents/test_fabric_agent/tasks.yaml
""")

    # Create fabric_agents directory
    fabric_agents_dir = crewai_dir / "fabric_agents" / "test_fabric_agent"
    fabric_agents_dir.mkdir(parents=True)

    # Create minimal agent and task configs
    (fabric_agents_dir / "agents.yaml").write_text("""
test_agent:
  role: Test Agent
  goal: Test goal
  backstory: Test backstory
""")

    (fabric_agents_dir / "tasks.yaml").write_text("""
test_task:
  description: Test task description
  expected_output: Test output
  agent: test_agent
""")

    return tmp_path


@pytest.fixture
def mock_fabric_agent_result() -> MagicMock:
    """Create a mock fabric agent result."""
    result = MagicMock()
    result.raw = {"output": "test output", "success": True}
    return result


@pytest.fixture
def check_api_key() -> None:
    """Skip live E2E tests when Anthropic credentials are unavailable."""
    if not os.environ.get("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")


@pytest.fixture
def check_aws_credentials() -> None:
    """Skip live E2E tests when AWS Bedrock credentials are unavailable."""
    has_key = os.environ.get("AWS_ACCESS_KEY_ID")
    has_profile = os.environ.get("AWS_PROFILE")
    if not (has_key or has_profile):
        pytest.skip("AWS credentials not configured; set AWS_ACCESS_KEY_ID or AWS_PROFILE")


@pytest.fixture
def temp_crewai_dir(tmp_path: Path) -> Path:
    """Create a temporary CrewAI config directory with minimal structure."""
    crewai_dir = tmp_path / "test_package" / ".crewai"
    crewai_dir.mkdir(parents=True)
    (crewai_dir / "fabric_agents").mkdir()
    return crewai_dir


@pytest.fixture
def simple_agent_config() -> dict[str, Any]:
    """Get a simple agent configuration for runner tests."""
    return {
        "role": "Test Agent",
        "goal": "Answer simple questions accurately",
        "backstory": "You are a helpful assistant focused on providing clear, concise answers.",
    }


@pytest.fixture
def simple_task_config() -> dict[str, Any]:
    """Get a simple task configuration for runner tests."""
    return {
        "description": "Answer the question: What is 2 + 2?",
        "expected_output": "The answer to the mathematical question",
    }


@pytest.fixture
def simple_fabric_agent_config(
    simple_agent_config: dict[str, Any],
    simple_task_config: dict[str, Any],
) -> dict[str, Any]:
    """Get a simple fabric agent configuration for runner tests."""
    return {
        "name": "test_fabric_agent",
        "description": "A simple test fabric agent",
        "agents": {"test_agent": simple_agent_config},
        "tasks": {
            "test_task": {
                **simple_task_config,
                "agent": "test_agent",
            },
        },
        "knowledge_paths": [],
    }


@pytest.fixture
def multi_agent_fabric_agent_config() -> dict[str, Any]:
    """Get a multi-agent fabric agent configuration for runner tests."""
    return {
        "name": "multi_agent_fabric_agent",
        "description": "A fabric agent with multiple collaborating agents",
        "agents": {
            "researcher": {
                "role": "Researcher",
                "goal": "Gather and analyze information",
                "backstory": "You are an expert researcher.",
            },
            "writer": {
                "role": "Writer",
                "goal": "Write clear summaries",
                "backstory": "You are a skilled technical writer.",
            },
        },
        "tasks": {
            "research_task": {
                "description": "Research the topic: Python programming",
                "expected_output": "Key facts about Python",
                "agent": "researcher",
            },
            "writing_task": {
                "description": "Write a brief summary based on the research",
                "expected_output": "A concise summary",
                "agent": "writer",
                "context": ["research_task"],
            },
        },
        "knowledge_paths": [],
    }


@pytest.fixture
def fabric_agent_with_knowledge(tmp_path: Path) -> dict[str, Any]:
    """Get a fabric agent configuration with a local knowledge source."""
    knowledge_dir = tmp_path / "knowledge"
    knowledge_dir.mkdir()
    (knowledge_dir / "test_info.md").write_text(
        """# Test Knowledge

This is test knowledge about the color blue.
Blue is a primary color.
It is often associated with calmness and stability.
""",
    )

    return {
        "name": "knowledge_fabric_agent",
        "description": "A fabric agent with knowledge sources",
        "agents": {
            "knowledgeable_agent": {
                "role": "Knowledge Expert",
                "goal": "Answer questions using provided knowledge",
                "backstory": "You have access to specialized knowledge.",
            },
        },
        "tasks": {
            "knowledge_task": {
                "description": "What color is mentioned in the knowledge base?",
                "expected_output": "The color mentioned",
                "agent": "knowledgeable_agent",
            },
        },
        "knowledge_paths": [knowledge_dir],
    }
