"""Tests for pytest-agentic-fabric."""

from __future__ import annotations

import sys

from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

from pytest_agentic_fabric.mocking import FabricMocker


pytest_plugins = ("pytester",)


def test_package_version_falls_back_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Source-tree imports should have a stable version fallback when not installed."""
    from importlib.metadata import PackageNotFoundError

    def missing_version(name: str) -> str:
        if name == "pytest-agentic-fabric":
            raise PackageNotFoundError(name)
        return "1.0.0"

    # Simulate the __init__.py version-fallback logic with a mocked version function.
    namespace: dict[str, Any] = {"version": missing_version, "PackageNotFoundError": PackageNotFoundError}
    exec(
        "try:\n"
        "    __version__ = version('pytest-agentic-fabric')\n"
        "except PackageNotFoundError:\n"
        "    __version__ = '0.2.0'\n",
        namespace,
    )

    assert namespace["__version__"] == "0.2.0"


def test_agentic_runtime_available_fixture(agentic_runtime_available: Callable[[str], bool]) -> None:
    """The runtime availability fixture should detect installed modules."""
    assert agentic_runtime_available("sys") is True
    assert agentic_runtime_available("module_that_should_not_exist_for_agentic_fabric_tests") is False


def test_agentic_runtime_registry_fixture(agentic_runtime_registry: dict[str, Any]) -> None:
    """The runtime registry fixture should be isolated and mutable."""
    agentic_runtime_registry["local"] = {"available": True}

    assert agentic_runtime_registry == {"local": {"available": True}}


def test_agentic_runtime_modules_fixture(agentic_runtime_modules: dict[str, tuple[str, ...]]) -> None:
    """Known runtime modules should be exposed for consumer tests."""
    assert agentic_runtime_modules["crewai"][0] == "crewai"
    assert "langgraph.prebuilt" in agentic_runtime_modules["langgraph"]
    assert agentic_runtime_modules["strands"] == ("strands",)


def test_agentic_mock_runtime_fixture(agentic_mock_runtime: Callable[[str], dict[str, ModuleType]]) -> None:
    """Runtime mocking fixture should install importable module objects."""
    modules = agentic_mock_runtime("langgraph")

    import langgraph.prebuilt

    assert modules["langgraph.prebuilt"] is langgraph.prebuilt
    assert langgraph.prebuilt.create_react_agent("llm", [])["args"] == ("llm", [])


@pytest.mark.parametrize("runtime,expected_attr", [("crewai", "Agent"), ("strands", "Agent")])
def test_agentic_mock_runtime_sets_runtime_entrypoints(
    agentic_mock_runtime: Callable[[str], dict[str, ModuleType]],
    runtime: str,
    expected_attr: str,
) -> None:
    """Runtime mocking fixture should install common runtime entrypoints."""
    modules = agentic_mock_runtime(runtime)

    assert hasattr(modules[runtime], expected_attr)


def test_fabric_mocker_properties(fabric_mocker: FabricMocker, mocker: Any) -> None:
    """The published mocker should expose pytest-mock helpers."""
    target = ModuleType("spy_target")
    target.func = lambda: "ok"

    assert fabric_mocker.MagicMock() is not None
    assert fabric_mocker.Mock() is not None
    patched: dict[str, bool] = {}
    fabric_mocker.patch.dict(patched, {"patched": True})
    assert patched["patched"] is True
    spy = fabric_mocker.spy(target, "func")
    assert target.func() == "ok"
    spy.assert_called_once_with()
    assert fabric_mocker.stub(name="stub") is not None
    assert fabric_mocker.mocker is mocker


def test_fabric_mocker_module_restore_handles_original_parent_attr(
    fabric_mocker: FabricMocker,
) -> None:
    """Mocked nested modules should restore previous parent attributes."""
    parent = ModuleType("parent_fixture")
    original_child = object()
    parent.child = original_child
    sys.modules["parent_fixture"] = parent

    try:
        child = fabric_mocker.mock_module("parent_fixture.child")

        assert parent.child is child

        fabric_mocker.restore_modules()

        assert parent.child is original_child
        assert "parent_fixture.child" not in sys.modules
    finally:
        sys.modules.pop("parent_fixture", None)


def test_fabric_mocker_restore_removes_new_parent_attr(fabric_mocker: FabricMocker) -> None:
    """Mocked nested modules should remove parent attributes they created."""
    parent = ModuleType("new_parent_fixture")
    sys.modules["new_parent_fixture"] = parent

    try:
        child = fabric_mocker.mock_module("new_parent_fixture.child")

        assert parent.child is child

        fabric_mocker.restore_modules()

        assert not hasattr(parent, "child")
    finally:
        sys.modules.pop("new_parent_fixture", None)


def test_fabric_mocker_returns_same_module_on_repeat(fabric_mocker: FabricMocker) -> None:
    """Repeated module mocks should reuse the same fake module."""
    assert fabric_mocker.mock_module("repeat_fixture") is fabric_mocker.mock_module("repeat_fixture")


def test_fabric_mocker_restores_original_module(fabric_mocker: FabricMocker) -> None:
    """Existing sys.modules entries should be restored."""
    original = ModuleType("existing_fixture")
    sys.modules["existing_fixture"] = original

    try:
        mocked = fabric_mocker.mock_module("existing_fixture")

        assert mocked is not original

        fabric_mocker.restore_modules()

        assert sys.modules["existing_fixture"] is original
    finally:
        sys.modules.pop("existing_fixture", None)


def test_fabric_mocker_crewai_helpers(fabric_mocker: FabricMocker) -> None:
    """CrewAI helpers should mock modules and common objects."""
    modules = fabric_mocker.mock_crewai()

    patched_agent = fabric_mocker.patch_crewai_agent()
    assert modules["crewai"].Agent is patched_agent
    assert fabric_mocker.patch_crewai_task() is not None
    assert fabric_mocker.patch_crewai_crew() is not None
    assert fabric_mocker.patch_crewai_process() is not None
    assert fabric_mocker.patch_knowledge_source() is modules[
        "crewai.knowledge.source.text_file_knowledge_source"
    ].TextFileKnowledgeSource
    assert fabric_mocker.mock_crewai_agent(role="Tester").role == "Tester"
    assert fabric_mocker.mock_crewai_task(description="Task").description == "Task"
    assert fabric_mocker.mock_crewai_crew(result="done").kickoff().raw == "done"


def test_fabric_mocker_langgraph_helpers(fabric_mocker: FabricMocker) -> None:
    """LangGraph helpers should mock modules and common objects."""
    modules = fabric_mocker.mock_langgraph()

    assert fabric_mocker.patch_create_react_agent() is modules["langgraph.prebuilt"].create_react_agent
    assert fabric_mocker.patch_chat_anthropic() is modules["langchain_anthropic"].ChatAnthropic
    assert fabric_mocker.mock_langgraph_graph(result="done").invoke()["messages"][0].content == "done"


def test_fabric_mocker_strands_helpers(fabric_mocker: FabricMocker) -> None:
    """Strands helpers should mock modules and common objects."""
    modules = fabric_mocker.mock_strands()

    assert fabric_mocker.patch_strands_agent() is modules["strands"].Agent
    assert fabric_mocker.mock_strands_agent(result="done")() == "done"


def test_fabric_mocker_patch_helpers_install_missing_frameworks(agentic_fabric_mocker: FabricMocker) -> None:
    """Patch helpers should lazily install framework modules when needed."""
    crewai_agent = agentic_fabric_mocker.patch_crewai_agent()
    langgraph_agent = agentic_fabric_mocker.patch_create_react_agent()
    strands_agent = agentic_fabric_mocker.patch_strands_agent()

    assert sys.modules["crewai"].Agent is crewai_agent
    assert sys.modules["langgraph"].prebuilt.create_react_agent is langgraph_agent
    assert sys.modules["strands"].Agent is strands_agent


def test_fabric_mocker_all_frameworks(mock_agentic_frameworks: dict[str, ModuleType]) -> None:
    """The all-framework fixture should install each supported runtime module."""
    assert "crewai" in mock_agentic_frameworks
    assert "langgraph.prebuilt" in mock_agentic_frameworks
    assert "strands" in mock_agentic_frameworks


def test_framework_specific_mock_fixtures(
    mock_crewai: dict[str, ModuleType],
    mock_langgraph: dict[str, ModuleType],
    mock_strands: dict[str, ModuleType],
) -> None:
    """Framework-specific fixtures should install only their runtime modules."""
    assert "crewai" in mock_crewai
    assert "langgraph.prebuilt" in mock_langgraph
    assert "strands" in mock_strands


def test_agentic_fabric_mocker_internal_patch_helpers(agentic_fabric_mocker: FabricMocker) -> None:
    """Agentic-fabric patch helpers should target fabric names."""
    llm = object()

    assert agentic_fabric_mocker.patch_get_llm(return_value=llm).return_value is llm
    assert agentic_fabric_mocker.patch_discover_packages({"pkg": Path(".fabric")}).return_value == {
        "pkg": Path(".fabric"),
    }
    assert agentic_fabric_mocker.patch_get_fabric_agent_config({"name": "custom"}).return_value == {
        "name": "custom",
    }
    assert agentic_fabric_mocker.patch_run_fabric_agent_auto("done").return_value == "done"


def test_agentic_fabric_agent_config_fixture(agentic_fabric_agent_config: dict[str, Any]) -> None:
    """Minimal fabric agent config should be usable by runtime tests."""
    assert agentic_fabric_agent_config["agents"]["tester"]["role"] == "Tester"
    assert agentic_fabric_agent_config["tasks"]["verify"]["agent"] == "tester"


def test_shared_config_fixtures(
    simple_agent_config: dict[str, Any],
    simple_task_config: dict[str, Any],
    simple_fabric_agent_config: dict[str, Any],
    multi_agent_fabric_agent_config: dict[str, Any],
    fabric_agent_with_knowledge: dict[str, Any],
    temp_fabric_dir: Path,
) -> None:
    """Shared config fixtures should be framework-neutral and discoverable."""
    assert simple_agent_config["role"] == "Test Agent"
    assert simple_task_config["description"].startswith("Answer the question")
    assert simple_fabric_agent_config["tasks"]["test_task"]["agent"] == "test_agent"
    assert multi_agent_fabric_agent_config["tasks"]["writing_task"]["context"] == ["research_task"]
    assert fabric_agent_with_knowledge["knowledge_paths"][0].joinpath("test_info.md").exists()
    assert temp_fabric_dir.name == ".fabric"
    assert temp_fabric_dir.joinpath("fabric_agents").is_dir()


def test_agentic_workspace_fixture(agentic_workspace: Path) -> None:
    """Workspace fixture should create a discoverable .fabric package."""
    manifest = agentic_workspace / "packages" / "sample" / ".fabric" / "manifest.yaml"
    agents = agentic_workspace / "packages" / "sample" / ".fabric" / "fabric_agents" / "test_fabric_agent" / "agents.yaml"
    tasks = agentic_workspace / "packages" / "sample" / ".fabric" / "fabric_agents" / "test_fabric_agent" / "tasks.yaml"

    assert manifest.exists()
    assert yaml.safe_load(manifest.read_text(encoding="utf-8"))["fabric_agents"]["test_fabric_agent"][
        "description"
    ] == "A test fabric agent"
    assert yaml.safe_load(agents.read_text(encoding="utf-8"))["tester"]["role"] == "Tester"
    assert yaml.safe_load(tasks.read_text(encoding="utf-8"))["verify"]["agent"] == "tester"


def test_agentic_workspace_fixture_uses_overridden_config(pytester: pytest.Pytester) -> None:
    """Workspace fixture should serialize overridden fabric agent configs."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makeconftest(
        """
        import pytest

        @pytest.fixture
        def agentic_fabric_agent_config():
            return {
                "name": "custom_agent",
                "description": "Custom description",
                "preferred_framework": "langgraph",
                "agents": {
                    "custom": {
                        "role": "Custom",
                        "goal": "Check override",
                        "backstory": "Fixture override",
                    },
                },
                "tasks": {
                    "custom_task": {
                        "description": "Use override",
                        "expected_output": "Override result",
                        "agent": "custom",
                    },
                },
            }
        """
    )
    pytester.makepyfile(
        """
        import yaml

        def test_workspace_uses_override(agentic_workspace):
            fabric_dir = agentic_workspace / "packages" / "sample" / ".fabric"
            manifest = yaml.safe_load((fabric_dir / "manifest.yaml").read_text(encoding="utf-8"))
            agent_config = manifest["fabric_agents"]["custom_agent"]
            agents = yaml.safe_load((fabric_dir / "fabric_agents" / "custom_agent" / "agents.yaml").read_text(encoding="utf-8"))
            tasks = yaml.safe_load((fabric_dir / "fabric_agents" / "custom_agent" / "tasks.yaml").read_text(encoding="utf-8"))

            assert agent_config["description"] == "Custom description"
            assert agent_config["preferred_framework"] == "langgraph"
            assert agents["custom"]["role"] == "Custom"
            assert tasks["custom_task"]["agent"] == "custom"
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(passed=1)


def test_check_api_key_fixture_skips_without_key(pytester: pytest.Pytester) -> None:
    """Credential fixtures should skip live tests when credentials are absent."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        def test_requires_api_key(check_api_key):
            assert True
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(skipped=1)


def test_check_aws_credentials_fixture_skips_without_credentials(pytester: pytest.Pytester) -> None:
    """AWS credential fixture should skip live tests when credentials are absent."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        def test_requires_aws(check_aws_credentials):
            assert True
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(skipped=1)


def test_agentic_e2e_marker_skips_by_default(pytester: pytest.Pytester) -> None:
    """Runtime-dependent tests should skip unless --agentic-e2e is passed."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.agentic_e2e
        def test_live_runtime():
            assert False
        """
    )

    result = pytester.runpytest("-q")

    result.assert_outcomes(skipped=1)


def test_agentic_e2e_marker_runs_when_enabled(pytester: pytest.Pytester) -> None:
    """Runtime-dependent tests should run when --agentic-e2e is passed."""
    pytester.makeini("[pytest]\nasyncio_default_fixture_loop_scope = function\n")
    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.agentic_e2e
        def test_live_runtime():
            assert True
        """
    )

    result = pytester.runpytest("-q", "--agentic-e2e")

    result.assert_outcomes(passed=1)
